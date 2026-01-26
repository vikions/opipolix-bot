import logging
from typing import Optional

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from tge_alert_config import DEFAULT_TGE_KEYWORDS, format_keywords
from tge_alert_db import TgeAlertDatabase
from tge_projects import list_project_names, match_project_name, get_project_config


logger = logging.getLogger(__name__)

TGE_ALERTS_MENU_TEXT = "🔔 TGE Project Alerts"
TGE_ALERTS_ADD_TEXT = "➕ Add Alert"
TGE_ALERTS_LIST_TEXT = "📋 My Alerts"
TGE_ALERTS_REMOVE_TEXT = "🔕 Remove Alert"
TGE_ALERTS_BACK_TEXT = "🔙 Back"
TGE_ALERTS_ENABLE_TEXT = "✅ Enable Alert"
TGE_ALERTS_DISABLE_TEXT = "🔕 Disable Alert"
TGE_ALERTS_SOON_TEXT = "Soon more"


db = TgeAlertDatabase()


def build_tge_alerts_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(TGE_ALERTS_ADD_TEXT), KeyboardButton(TGE_ALERTS_LIST_TEXT)],
        [KeyboardButton(TGE_ALERTS_REMOVE_TEXT)],
        [KeyboardButton(TGE_ALERTS_BACK_TEXT)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_tge_alerts_manage_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(TGE_ALERTS_ENABLE_TEXT), KeyboardButton(TGE_ALERTS_DISABLE_TEXT)],
        [KeyboardButton(TGE_ALERTS_REMOVE_TEXT)],
        [KeyboardButton(TGE_ALERTS_BACK_TEXT)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_tge_projects_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    buffer = []

    for name in list_project_names():
        buffer.append(KeyboardButton(name))
        if len(buffer) == 2:
            rows.append(buffer)
            buffer = []

    if buffer:
        rows.append(buffer)

    rows.append([KeyboardButton(TGE_ALERTS_SOON_TEXT)])
    rows.append([KeyboardButton(TGE_ALERTS_BACK_TEXT)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def show_tge_alerts_menu(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("pending_tge_alert", None)
    await message.reply_text(
        "TGE Project Alerts\n\n"
        "Monitor Discord and Twitter for token launch announcements.",
        reply_markup=build_tge_alerts_menu_keyboard(),
    )


async def handle_add_tge_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["pending_tge_alert"] = {"step": "project"}
    await update.message.reply_text(
        "Select a project to monitor:",
        reply_markup=build_tge_projects_keyboard(),
    )


async def handle_my_tge_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.message.from_user.id
    alerts = db.get_user_alerts(telegram_id)

    if not alerts:
        await update.message.reply_text(
            "My TGE Alerts\n\n"
            "You do not have any alerts yet.\n\n"
            f"Use '{TGE_ALERTS_ADD_TEXT}' to add one.",
            reply_markup=build_tge_alerts_menu_keyboard(),
        )
        return

    lines = ["My TGE Alerts\n"]
    for alert in alerts:
        status = "active" if alert.get("active") else "disabled"
        lines.append(f"- #{alert.get('id')} {alert.get('project_name')} | {status}")

    lines.append("")
    lines.append("Use the buttons below and send the alert ID.")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=build_tge_alerts_manage_keyboard(),
    )


async def handle_remove_tge_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["pending_tge_alert"] = {"step": "remove_id"}
    await update.message.reply_text(
        "Send the alert ID to remove:",
        reply_markup=build_tge_alerts_manage_keyboard(),
    )


async def handle_toggle_tge_alert(
    update: Update, context: ContextTypes.DEFAULT_TYPE, enable: bool
) -> None:
    context.user_data["pending_tge_alert"] = {"step": "toggle_id", "enable": enable}
    action = "enable" if enable else "disable"
    await update.message.reply_text(
        f"Send the alert ID to {action}:",
        reply_markup=build_tge_alerts_manage_keyboard(),
    )


async def handle_pending_tge_alert_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> bool:
    pending = context.user_data.get("pending_tge_alert")
    if not pending:
        return False

    if text == TGE_ALERTS_BACK_TEXT:
        await show_tge_alerts_menu(update.message, context)
        return True

    step = pending.get("step")

    if step == "project":
        if text == TGE_ALERTS_SOON_TEXT:
            await update.message.reply_text(
                "More projects coming soon.",
                reply_markup=build_tge_projects_keyboard(),
            )
            return True

        project_name = match_project_name(text)
        if not project_name:
            await update.message.reply_text(
                "Please select a project from the list.",
                reply_markup=build_tge_projects_keyboard(),
            )
            return True

        config = get_project_config(project_name)
        discord_channel_id = config.discord_channel_id if config else None

        alert_id = db.create_or_update_alert(
            telegram_id=update.message.from_user.id,
            project_name=project_name,
            discord_channel_id=discord_channel_id,
            keywords=DEFAULT_TGE_KEYWORDS,
            active=True,
        )

        keywords_display = format_keywords(DEFAULT_TGE_KEYWORDS)
        channel_label = discord_channel_id or "not configured"

        message = (
            "Alert created.\n\n"
            f"Project: {project_name}\n"
            f"Discord channel: {channel_label}\n"
            f"Keywords: {keywords_display}\n"
            f"Alert ID: {alert_id}\n"
        )

        if not discord_channel_id:
            message += "\nDiscord channel not configured for this project."

        await update.message.reply_text(
            message,
            reply_markup=build_tge_alerts_menu_keyboard(),
        )

        context.user_data.pop("pending_tge_alert", None)
        logger.info("TGE alert created for %s (id=%s)", project_name, alert_id)
        return True

    if step in {"remove_id", "toggle_id"}:
        try:
            alert_id = int(text)
        except ValueError:
            await update.message.reply_text("Alert ID must be a number.")
            return True

        telegram_id = update.message.from_user.id
        alerts = db.get_user_alerts(telegram_id)
        alert = next((item for item in alerts if item.get("id") == alert_id), None)

        if not alert:
            await update.message.reply_text("Alert not found for your account.")
            return True

        if step == "remove_id":
            db.remove_alert(alert_id)
            await update.message.reply_text(
                f"Alert #{alert_id} removed.",
                reply_markup=build_tge_alerts_menu_keyboard(),
            )
            logger.info("TGE alert removed (id=%s)", alert_id)
        else:
            enable = bool(pending.get("enable"))
            db.set_alert_active(alert_id, enable)
            status = "enabled" if enable else "disabled"
            await update.message.reply_text(
                f"Alert #{alert_id} {status}.",
                reply_markup=build_tge_alerts_menu_keyboard(),
            )
            logger.info("TGE alert %s (id=%s)", status, alert_id)

        context.user_data.pop("pending_tge_alert", None)
        return True

    return False

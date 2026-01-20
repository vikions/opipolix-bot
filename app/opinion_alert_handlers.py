import re
from typing import Optional

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

from database import Database
from opinion_tracked_markets import WHITELIST_CHILD_IDS, CHILD_TO_PROJECT


ALERTS_CREATE_TEXT = "Create Alert"
ALERTS_LIST_TEXT = "My Alerts"
ALERTS_BACK_TEXT = "Back to Opinion Markets"
ALERTS_FLOW_BACK_TEXT = "Back to Alerts"

ALERT_TYPE_PUMP_TEXT = "Price Pump"
ALERT_TYPE_DUMP_TEXT = "Price Dump"


_MARKET_ID_PATTERN = re.compile(r"(\d+)")
_TOP_MARKET_IDS = WHITELIST_CHILD_IDS[:10]

db = Database()


def _market_label(market_id: int) -> str:
    name = CHILD_TO_PROJECT.get(market_id)
    if name:
        return f"{name} ({market_id})"
    return f"Market {market_id}"


def _parse_market_id(text: str) -> Optional[int]:
    match = _MARKET_ID_PATTERN.search(text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def build_opinion_alerts_menu_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(ALERTS_CREATE_TEXT), KeyboardButton(ALERTS_LIST_TEXT)],
        [KeyboardButton(ALERTS_BACK_TEXT)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_opinion_alert_market_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    buffer = []

    for market_id in _TOP_MARKET_IDS:
        buffer.append(KeyboardButton(_market_label(market_id)))
        if len(buffer) == 2:
            rows.append(buffer)
            buffer = []

    if buffer:
        rows.append(buffer)

    rows.append([KeyboardButton(ALERTS_FLOW_BACK_TEXT)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_opinion_alert_type_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(ALERT_TYPE_PUMP_TEXT), KeyboardButton(ALERT_TYPE_DUMP_TEXT)],
        [KeyboardButton(ALERTS_FLOW_BACK_TEXT)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def show_opinion_alerts_menu(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("pending_opinion_alert", None)

    await message.reply_text(
        "Opinion Alerts\n\n"
        "Create alerts for tracked Opinion markets.",
        reply_markup=build_opinion_alerts_menu_keyboard()
    )


async def handle_create_opinion_alert(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data["pending_opinion_alert"] = {"step": "market"}

    await update.message.reply_text(
        "Select a market for the alert:",
        reply_markup=build_opinion_alert_market_keyboard()
    )


async def handle_my_opinion_alerts(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    telegram_id = update.message.from_user.id
    alerts = db.get_user_opinion_alerts(telegram_id)

    if not alerts:
        await update.message.reply_text(
            "My Opinion Alerts\n\n"
            "You do not have any alerts yet.\n\n"
            f"Use '{ALERTS_CREATE_TEXT}' to add one.",
            reply_markup=build_opinion_alerts_menu_keyboard()
        )
        return

    lines = ["My Opinion Alerts\n"]

    for alert in alerts:
        market_id = alert.get("market_id")
        project = CHILD_TO_PROJECT.get(market_id, f"Market {market_id}")
        alert_type = alert.get("alert_type")
        trigger_percent = alert.get("trigger_percent", 0)
        status = alert.get("status", "active")

        type_label = "Pump" if alert_type == "price_pump" else "Dump"

        try:
            trigger_display = f"{float(trigger_percent):.2f}%"
        except Exception:
            trigger_display = f"{trigger_percent}%"

        lines.append(
            f"- #{alert.get('id')} {project} | {type_label} {trigger_display} | {status}"
        )

    lines.append("")
    lines.append("Cancel: /cancelalert <id>")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=build_opinion_alerts_menu_keyboard()
    )


async def handle_pending_opinion_alert_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str
) -> bool:
    pending = context.user_data.get("pending_opinion_alert")

    if not pending:
        return False

    if text == ALERTS_FLOW_BACK_TEXT:
        await show_opinion_alerts_menu(update.message, context)
        return True

    step = pending.get("step")

    if step == "market":
        market_id = _parse_market_id(text)

        if market_id is None or market_id not in _TOP_MARKET_IDS:
            await update.message.reply_text(
                "Please select a market from the list.",
                reply_markup=build_opinion_alert_market_keyboard()
            )
            return True

        pending["market_id"] = market_id
        pending["step"] = "type"

        await update.message.reply_text(
            "Select alert type:",
            reply_markup=build_opinion_alert_type_keyboard()
        )
        return True

    if step == "type":
        if text == ALERT_TYPE_PUMP_TEXT:
            pending["alert_type"] = "price_pump"
        elif text == ALERT_TYPE_DUMP_TEXT:
            pending["alert_type"] = "price_dump"
        else:
            await update.message.reply_text(
                "Please choose a valid alert type.",
                reply_markup=build_opinion_alert_type_keyboard()
            )
            return True

        pending["step"] = "percent"

        await update.message.reply_text(
            "Enter trigger percentage (e.g. 10, 25, 50):"
        )
        return True

    if step == "percent":
        try:
            trigger_percent = float(text)
        except ValueError:
            await update.message.reply_text("Please send a valid number.")
            return True

        if trigger_percent <= 0 or trigger_percent > 500:
            await update.message.reply_text(
                "Trigger percent must be between 1 and 500."
            )
            return True

        telegram_id = update.message.from_user.id
        market_id = pending.get("market_id")
        alert_type = pending.get("alert_type")

        alert_id = db.create_opinion_alert(
            telegram_id=telegram_id,
            market_id=market_id,
            alert_type=alert_type,
            trigger_percent=trigger_percent
        )

        project = CHILD_TO_PROJECT.get(market_id, f"Market {market_id}")
        type_label = "Pump" if alert_type == "price_pump" else "Dump"

        await update.message.reply_text(
            "Alert created.\n\n"
            f"Market: {project}\n"
            f"Type: {type_label}\n"
            f"Trigger: {trigger_percent:.2f}%\n"
            f"Alert ID: {alert_id}\n\n"
            "Cancel with: /cancelalert <id>",
            reply_markup=build_opinion_alerts_menu_keyboard()
        )

        context.user_data.pop("pending_opinion_alert", None)
        return True

    return False


async def cancel_opinion_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.from_user.id

    if not context.args:
        await update.message.reply_text(
            "Usage: /cancelalert <id>\nExample: /cancelalert 1"
        )
        return

    try:
        alert_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Alert ID must be a number.")
        return

    alerts = db.get_user_opinion_alerts(telegram_id)
    alert = next((a for a in alerts if a.get("id") == alert_id), None)

    if not alert:
        await update.message.reply_text(
            f"Alert #{alert_id} not found."
        )
        return

    if alert.get("status") != "active":
        await update.message.reply_text(
            f"Alert #{alert_id} is already {alert.get('status')}."
        )
        return

    db.update_opinion_alert_status(alert_id, "cancelled")

    await update.message.reply_text(
        f"Alert #{alert_id} cancelled.",
        reply_markup=build_opinion_alerts_menu_keyboard()
    )

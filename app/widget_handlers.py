from datetime import datetime
from typing import Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from market_config import get_all_markets
from widget_db import WidgetDatabase
from widget_markets import get_market_snapshots
from widget_renderer import compute_market_hash, render_widget_text
from widget_updater import update_widget_message


logger = logging.getLogger(__name__)


BTN_WIDGET_MENU = "📌 Telegram Widget"

CB_WIDGET_MENU = "widget_menu"
CB_WIDGET_CREATE = "widget_create"
CB_WIDGET_MANAGE = "widget_manage"
CB_WIDGET_PERMS = "widget_permissions"
CB_WIDGET_ADDED = "widget_added_bot"

CB_WIDGET_CHAT_PREFIX = "widget_chat:"
CB_WIDGET_MARKET_TOGGLE_PREFIX = "widget_market_toggle:"
CB_WIDGET_INTERVAL_PREFIX = "widget_interval:"
CB_WIDGET_MANAGE_PREFIX = "widget_manage_select:"
CB_WIDGET_ACTION_PREFIX = "widget_action:"


INTERVAL_OPTIONS = [30, 60, 120, 300]

db = WidgetDatabase()

ALL_MARKETS = get_all_markets()
ALL_MARKET_ALIASES = list(ALL_MARKETS.keys())

POPULAR_MARKETS = [
    alias
    for alias in ["opinion", "opensea", "metamask", "base", "abstract", "polymarket"]
    if alias in ALL_MARKETS
]
RECENT_MARKETS = [alias for alias in ALL_MARKET_ALIASES[-5:] if alias in ALL_MARKETS]


def _market_title(alias: str) -> str:
    market = ALL_MARKETS.get(alias)
    if not market:
        return alias
    return market.get("title") or alias


def _format_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def _permissions_instructions_text() -> str:
    return (
        "📌 Telegram Widget — Permissions\n\n"
        "Add @OpiPolixBot to your group/channel and make it admin with ONLY:\n"
        "• Pin messages\n"
        "• Edit messages\n\n"
        "Then tap the button below."
    )


def _permissions_howto_text() -> str:
    return (
        "ℹ️ Permissions / How-to\n\n"
        "The bot only needs:\n"
        "• Pin messages — to keep the widget at the top\n"
        "• Edit messages — to update its own widget message\n\n"
        "The bot cannot delete user messages, ban users, or read private messages."
    )


def build_widget_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("➕ Create widget", callback_data=CB_WIDGET_CREATE)],
        [InlineKeyboardButton("🛠 Manage widgets", callback_data=CB_WIDGET_MANAGE)],
        [InlineKeyboardButton("ℹ️ Permissions / How-to", callback_data=CB_WIDGET_PERMS)],
    ]
    return InlineKeyboardMarkup(rows)

def _widget_menu_text() -> str:
    return (
        "📌 Telegram Widget\n\n"
        "Create a pinned board message in your group/channel that shows live YES/NO "
        "values for selected markets. The bot edits the same message on schedule "
        "(no spam)."
    )


def build_permissions_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✅ I’ve added the bot", callback_data=CB_WIDGET_ADDED)],
        [InlineKeyboardButton("⬅️ Back", callback_data=CB_WIDGET_MENU)],
    ]
    return InlineKeyboardMarkup(rows)


def build_info_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=CB_WIDGET_MENU)]])


def build_chat_selection_keyboard(chats: List[Dict[str, object]]) -> InlineKeyboardMarkup:
    rows = []
    for chat in chats:
        title = chat.get("chat_title") or str(chat.get("chat_id"))
        label = title if len(title) <= 48 else f"{title[:45]}..."
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"{CB_WIDGET_CHAT_PREFIX}{chat.get('chat_id')}")]
        )
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=CB_WIDGET_MENU)])
    return InlineKeyboardMarkup(rows)


def build_market_selection_keyboard(
    selected: List[str], view_aliases: List[str]
) -> InlineKeyboardMarkup:
    rows = []
    for alias in view_aliases:
        title = _market_title(alias)
        is_selected = alias in selected
        prefix = "✅" if is_selected else "➕"
        label = f"{prefix} {title}"
        rows.append([InlineKeyboardButton(label, callback_data=f"{CB_WIDGET_MARKET_TOGGLE_PREFIX}{alias}")])

    rows.append(
        [
            InlineKeyboardButton("⭐ Popular", callback_data="widget_market_popular"),
            InlineKeyboardButton("🕒 Recent", callback_data="widget_market_recent"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton("🔍 Search", callback_data="widget_market_search"),
            InlineKeyboardButton("✅ Done", callback_data="widget_market_done"),
        ]
    )
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=CB_WIDGET_MENU)])
    return InlineKeyboardMarkup(rows)


def build_interval_keyboard(selected_seconds: int, confirm_label: str) -> InlineKeyboardMarkup:
    rows = []
    for seconds in INTERVAL_OPTIONS:
        label = _format_interval(seconds)
        if seconds == selected_seconds:
            label = f"✅ {label}"
        rows.append([InlineKeyboardButton(label, callback_data=f"{CB_WIDGET_INTERVAL_PREFIX}{seconds}")])

    rows.append([InlineKeyboardButton(confirm_label, callback_data="widget_interval_confirm")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=CB_WIDGET_MENU)])
    return InlineKeyboardMarkup(rows)


def build_manage_list_keyboard(widgets: List[Dict[str, object]]) -> InlineKeyboardMarkup:
    rows = []
    for widget in widgets:
        widget_id = widget.get("widget_id")
        label = f"Widget #{widget_id}"
        rows.append([InlineKeyboardButton(label, callback_data=f"{CB_WIDGET_MANAGE_PREFIX}{widget_id}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=CB_WIDGET_MENU)])
    return InlineKeyboardMarkup(rows)


def build_widget_actions_keyboard(widget: Dict[str, object]) -> InlineKeyboardMarkup:
    widget_id = widget.get("widget_id")
    enabled = bool(widget.get("enabled"))
    toggle_label = "⏸ Pause" if enabled else "▶️ Resume"
    toggle_action = "pause" if enabled else "resume"
    compact_mode = bool(widget.get("compact_mode", True))
    compact_label = "Compact view: ON" if compact_mode else "Compact view: OFF"

    rows = [
        [InlineKeyboardButton(toggle_label, callback_data=f"{CB_WIDGET_ACTION_PREFIX}{toggle_action}:{widget_id}")],
        [InlineKeyboardButton("🛠 Edit markets", callback_data=f"{CB_WIDGET_ACTION_PREFIX}edit_markets:{widget_id}")],
        [InlineKeyboardButton("⏱ Change interval", callback_data=f"{CB_WIDGET_ACTION_PREFIX}edit_interval:{widget_id}")],
        [InlineKeyboardButton(compact_label, callback_data=f"{CB_WIDGET_ACTION_PREFIX}toggle_compact:{widget_id}")],
        [InlineKeyboardButton("🔄 Refresh now", callback_data=f"{CB_WIDGET_ACTION_PREFIX}refresh:{widget_id}")],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"{CB_WIDGET_ACTION_PREFIX}delete:{widget_id}")],
        [InlineKeyboardButton("⬅️ Back", callback_data=CB_WIDGET_MANAGE)],
    ]
    return InlineKeyboardMarkup(rows)


def _default_selected_markets() -> List[str]:
    if POPULAR_MARKETS:
        return POPULAR_MARKETS[:3]
    return ALL_MARKET_ALIASES[:3]


def record_chat_from_update(update: Update) -> None:
    chat = update.effective_chat
    if not chat:
        return
    if chat.type in {"group", "supergroup", "channel"}:
        title = chat.title or chat.username or str(chat.id)
        db.record_chat(chat.id, title, chat.type)


async def widget_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    if update.effective_chat and update.effective_chat.type != "private":
        record_chat_from_update(update)
        try:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=_widget_menu_text(),
                reply_markup=build_widget_menu_keyboard(),
            )
            await message.reply_text("I’ve sent you a DM with the widget menu.")
        except TelegramError:
            await message.reply_text("Please DM me to set up the widget.")
        return

    context.user_data.pop("widget_pending", None)
    await message.reply_text(_widget_menu_text(), reply_markup=build_widget_menu_keyboard())


async def _send_permissions_instructions(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=chat_id,
        text=_permissions_instructions_text(),
        reply_markup=build_permissions_keyboard(),
    )


async def _show_manage_list(target, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    widgets = db.get_user_widgets(user_id)

    if not widgets:
        await target.reply_text(
            "You don’t have any widgets yet.\n\nUse ➕ Create widget to get started.",
            reply_markup=build_widget_menu_keyboard(),
        )
        return

    lines = ["Your widgets:\n"]
    for widget in widgets:
        chat_title = widget.get("chat_title") or str(widget.get("target_chat_id"))
        markets_count = len(widget.get("selected_market_ids") or [])
        interval_label = _format_interval(int(widget.get("interval_seconds") or 0))
        status = "Enabled" if widget.get("enabled") else "Paused"
        lines.append(
            f"#{widget.get('widget_id')} {chat_title} — {markets_count} markets — {interval_label} — {status}"
        )

    await target.reply_text(
        "\n".join(lines),
        reply_markup=build_manage_list_keyboard(widgets),
    )


def _market_view_aliases(pending: Dict[str, object]) -> List[str]:
    view = pending.get("market_view") or "popular"
    if view == "recent":
        return RECENT_MARKETS or ALL_MARKET_ALIASES
    if view == "search":
        query = str(pending.get("search_query") or "").lower()
        if not query:
            return ALL_MARKET_ALIASES
        matches = [
            alias
            for alias in ALL_MARKET_ALIASES
            if query in alias.lower() or query in _market_title(alias).lower()
        ]
        return matches or []
    return POPULAR_MARKETS or ALL_MARKET_ALIASES


async def _show_market_selection(target, context: ContextTypes.DEFAULT_TYPE) -> None:
    pending = context.user_data.get("widget_pending") or {}
    selected = pending.get("selected_markets") or []
    view_aliases = _market_view_aliases(pending)

    if not view_aliases:
        view_aliases = ALL_MARKET_ALIASES

    text_lines = [
        "Select markets to display (1–5). Default is 3.",
        f"Selected: {len(selected)}/5",
        "Tap to toggle, then press Done.",
    ]
    if pending.get("market_view") == "search" and pending.get("search_query"):
        text_lines.append(f"Search: {pending.get('search_query')}")

    message = await target.reply_text(
        "\n".join(text_lines),
        reply_markup=build_market_selection_keyboard(selected, view_aliases),
    )

    pending["selection_message_id"] = message.message_id
    pending["selection_chat_id"] = message.chat_id
    context.user_data["widget_pending"] = pending


async def _edit_market_selection_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    pending = context.user_data.get("widget_pending") or {}
    chat_id = pending.get("selection_chat_id")
    message_id = pending.get("selection_message_id")
    if not chat_id or not message_id:
        return

    selected = pending.get("selected_markets") or []
    view_aliases = _market_view_aliases(pending)
    if not view_aliases:
        view_aliases = ALL_MARKET_ALIASES

    text_lines = [
        "Select markets to display (1–5). Default is 3.",
        f"Selected: {len(selected)}/5",
        "Tap to toggle, then press Done.",
    ]
    if pending.get("market_view") == "search" and pending.get("search_query"):
        text_lines.append(f"Search: {pending.get('search_query')}")

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="\n".join(text_lines),
            reply_markup=build_market_selection_keyboard(selected, view_aliases),
        )
    except TelegramError:
        logger.exception("Failed to update market selection message")


async def _show_interval_selection(target, context: ContextTypes.DEFAULT_TYPE, confirm_label: str) -> None:
    pending = context.user_data.get("widget_pending") or {}
    selected = int(pending.get("interval_seconds") or 60)
    text = (
        "Choose update interval:\n"
        "We update only if values changed to respect Telegram limits."
    )
    message = await target.reply_text(
        text,
        reply_markup=build_interval_keyboard(selected, confirm_label),
    )
    pending["interval_message_id"] = message.message_id
    pending["interval_chat_id"] = message.chat_id
    context.user_data["widget_pending"] = pending


async def handle_pending_widget_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> bool:
    pending = context.user_data.get("widget_pending")
    if not pending or not pending.get("awaiting_search"):
        return False

    pending["awaiting_search"] = False
    pending["market_view"] = "search"
    pending["search_query"] = text.strip()
    context.user_data["widget_pending"] = pending

    await _edit_market_selection_message(context)
    return True


async def _get_bot_id(context: ContextTypes.DEFAULT_TYPE) -> int:
    cached = context.bot_data.get("bot_id")
    if cached:
        return cached
    me = await context.bot.get_me()
    context.bot_data["bot_id"] = me.id
    return me.id


def _has_required_permissions(member, chat_type: str) -> bool:
    if member.status == "creator":
        return True
    if member.status != "administrator":
        return False
    can_pin = bool(getattr(member, "can_pin_messages", False))
    can_edit = getattr(member, "can_edit_messages", None)
    if can_edit is None and chat_type in {"group", "supergroup"}:
        can_edit = True
    return bool(can_pin and can_edit)


async def _eligible_chats(context: ContextTypes.DEFAULT_TYPE) -> List[Dict[str, object]]:
    known_chats = db.get_known_chats()
    if not known_chats:
        return []

    bot_id = await _get_bot_id(context)
    eligible: List[Dict[str, object]] = []

    for chat in known_chats:
        chat_id = chat.get("chat_id")
        if not chat_id:
            continue
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=bot_id)
        except TelegramError:
            continue
        chat_type = chat.get("chat_type") or ""
        if _has_required_permissions(member, chat_type):
            eligible.append(chat)
    return eligible


async def _send_widget_created(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_title: str
) -> None:
    message = (
        "✅ Widget created!\n\n"
        f"Chat: {chat_title}\n"
        "Your board is pinned and will update automatically."
    )
    await context.bot.send_message(chat_id=user_id, text=message)


async def _create_widget(
    context: ContextTypes.DEFAULT_TYPE,
    owner_id: int,
    target_chat_id: int,
    selected_markets: List[str],
    interval_seconds: int,
) -> bool:
    chat_title = str(target_chat_id)
    for chat in db.get_known_chats():
        if chat.get("chat_id") == target_chat_id:
            chat_title = chat.get("chat_title") or chat_title
            break
    existing = db.get_widget_by_chat(target_chat_id)
    if existing:
        await context.bot.send_message(
            chat_id=owner_id,
            text="A widget already exists in that chat. Use 🛠 Manage widgets to edit it.",
        )
        return False

    snapshots = await get_market_snapshots(selected_markets)
    if not snapshots:
        await context.bot.send_message(
            chat_id=owner_id,
            text="⚠️ Unable to fetch market data right now. Please try again.",
        )
        return False

    now = datetime.utcnow()
    render_text = render_widget_text(snapshots, now, compact_mode=True)
    render_hash = compute_market_hash(snapshots, compact_mode=True)

    try:
        message = await context.bot.send_message(
            chat_id=target_chat_id,
            text=render_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except TelegramError:
        await context.bot.send_message(
            chat_id=owner_id,
            text="❌ I couldn’t post in that chat. Please check bot permissions and try again.",
        )
        return False

    try:
        await context.bot.pin_chat_message(
            chat_id=target_chat_id,
            message_id=message.message_id,
            disable_notification=True,
        )
    except TelegramError:
        await context.bot.send_message(
            chat_id=owner_id,
            text="❌ I couldn’t pin the widget. Please ensure the bot has Pin messages permission.",
        )
        return False

    widget_id = db.create_widget(
        owner_user_id=owner_id,
        target_chat_id=target_chat_id,
        board_message_id=message.message_id,
        selected_market_ids=selected_markets,
        interval_seconds=interval_seconds,
        enabled=True,
        compact_mode=True,
        last_render_hash=render_hash,
        last_rendered_at=now,
        last_heartbeat_at=now,
    )

    await _send_widget_created(context, owner_id, chat_title)
    logger.info("Widget created %s for chat %s", widget_id, target_chat_id)
    return True


async def handle_widget_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    await query.answer()

    if data in {CB_WIDGET_MENU, CB_WIDGET_CREATE, CB_WIDGET_MANAGE, CB_WIDGET_PERMS}:
        if data == CB_WIDGET_MENU:
            context.user_data.pop("widget_pending", None)
            await query.edit_message_text(
                BTN_WIDGET_MENU,
                reply_markup=build_widget_menu_keyboard(),
            )
            return

        if data == CB_WIDGET_CREATE:
            if update.effective_chat and update.effective_chat.type != "private":
                await query.edit_message_text("Please DM me to continue.")
                return
            context.user_data["widget_pending"] = {"step": "permissions"}
            await query.edit_message_text(
                _permissions_instructions_text(),
                reply_markup=build_permissions_keyboard(),
            )
            return

        if data == CB_WIDGET_MANAGE:
            await _show_manage_list(query.message, context, query.from_user.id)
            return

        if data == CB_WIDGET_PERMS:
            await query.edit_message_text(
                _permissions_howto_text(),
                reply_markup=build_info_keyboard(),
            )
            return

    if data == CB_WIDGET_ADDED:
        eligible = await _eligible_chats(context)
        if not eligible:
            await query.edit_message_text(
                "No eligible chats found.\n\n"
                "Send any message in the group so I can detect it, then try again.\n\n"
                + _permissions_instructions_text(),
                reply_markup=build_permissions_keyboard(),
            )
            return

        context.user_data["widget_pending"] = {
            "step": "select_chat",
            "eligible_chat_ids": [chat.get("chat_id") for chat in eligible],
        }
        await query.edit_message_text(
            "Select a chat for the widget:",
            reply_markup=build_chat_selection_keyboard(eligible),
        )
        return

    if data.startswith(CB_WIDGET_CHAT_PREFIX):
        chat_id = data.replace(CB_WIDGET_CHAT_PREFIX, "").strip()
        try:
            chat_id_int = int(chat_id)
        except ValueError:
            await query.answer("Invalid chat.", show_alert=True)
            return

        pending = context.user_data.get("widget_pending") or {}
        eligible_ids = pending.get("eligible_chat_ids") or []
        if eligible_ids and chat_id_int not in eligible_ids:
            await query.answer("Chat not eligible.", show_alert=True)
            return

        pending = {
            "step": "select_markets",
            "mode": "create",
            "target_chat_id": chat_id_int,
            "selected_markets": _default_selected_markets(),
            "market_view": "popular",
        }
        context.user_data["widget_pending"] = pending
        await query.edit_message_text(
            "Select markets to display (1–5). Default is 3.",
            reply_markup=build_market_selection_keyboard(
                pending["selected_markets"], _market_view_aliases(pending)
            ),
        )
        pending["selection_message_id"] = query.message.message_id
        pending["selection_chat_id"] = query.message.chat_id
        return

    if data.startswith(CB_WIDGET_MARKET_TOGGLE_PREFIX):
        alias = data.replace(CB_WIDGET_MARKET_TOGGLE_PREFIX, "").strip()
        pending = context.user_data.get("widget_pending") or {}
        selected = pending.get("selected_markets") or []
        if alias not in ALL_MARKETS:
            await query.answer("Unknown market.", show_alert=True)
            return

        if alias in selected:
            selected.remove(alias)
        else:
            if len(selected) >= 5:
                await query.answer("Maximum 5 markets.", show_alert=True)
                return
            selected.append(alias)

        pending["selected_markets"] = selected
        context.user_data["widget_pending"] = pending
        await query.edit_message_text(
            "Select markets to display (1–5). Default is 3.",
            reply_markup=build_market_selection_keyboard(
                selected, _market_view_aliases(pending)
            ),
        )
        return

    if data == "widget_market_popular":
        pending = context.user_data.get("widget_pending") or {}
        pending["market_view"] = "popular"
        pending.pop("search_query", None)
        context.user_data["widget_pending"] = pending
        await query.edit_message_text(
            "Select markets to display (1–5). Default is 3.",
            reply_markup=build_market_selection_keyboard(
                pending.get("selected_markets") or [], _market_view_aliases(pending)
            ),
        )
        return

    if data == "widget_market_recent":
        pending = context.user_data.get("widget_pending") or {}
        pending["market_view"] = "recent"
        pending.pop("search_query", None)
        context.user_data["widget_pending"] = pending
        await query.edit_message_text(
            "Select markets to display (1–5). Default is 3.",
            reply_markup=build_market_selection_keyboard(
                pending.get("selected_markets") or [], _market_view_aliases(pending)
            ),
        )
        return

    if data == "widget_market_search":
        pending = context.user_data.get("widget_pending") or {}
        pending["awaiting_search"] = True
        pending["market_view"] = "search"
        context.user_data["widget_pending"] = pending
        await query.message.reply_text("Send a keyword to filter markets:")
        return

    if data == "widget_market_done":
        pending = context.user_data.get("widget_pending") or {}
        selected = pending.get("selected_markets") or []
        if not selected:
            await query.answer("Select at least 1 market.", show_alert=True)
            return

        if pending.get("mode") == "edit_markets":
            widget_id = pending.get("widget_id")
            if widget_id:
                db.update_widget_markets(int(widget_id), selected)
                db.mark_widget_dirty(int(widget_id))
            context.user_data.pop("widget_pending", None)
            await query.edit_message_text(
                "✅ Markets updated.",
                reply_markup=build_widget_menu_keyboard(),
            )
            return

        pending["step"] = "select_interval"
        pending.setdefault("interval_seconds", 60)
        context.user_data["widget_pending"] = pending
        await query.edit_message_text(
            "Choose update interval:\nWe update only if values changed to respect Telegram limits.",
            reply_markup=build_interval_keyboard(
                int(pending.get("interval_seconds") or 60),
                "✅ Create widget",
            ),
        )
        return

    if data.startswith(CB_WIDGET_INTERVAL_PREFIX):
        seconds_str = data.replace(CB_WIDGET_INTERVAL_PREFIX, "").strip()
        try:
            seconds = int(seconds_str)
        except ValueError:
            await query.answer("Invalid interval.", show_alert=True)
            return

        pending = context.user_data.get("widget_pending") or {}
        pending["interval_seconds"] = seconds
        context.user_data["widget_pending"] = pending
        confirm_label = "✅ Create widget"
        if pending.get("mode") == "edit_interval":
            confirm_label = "✅ Save interval"
        await query.edit_message_text(
            "Choose update interval:\nWe update only if values changed to respect Telegram limits.",
            reply_markup=build_interval_keyboard(seconds, confirm_label),
        )
        return

    if data == "widget_interval_confirm":
        pending = context.user_data.get("widget_pending") or {}
        mode = pending.get("mode") or "create"
        interval_seconds = int(pending.get("interval_seconds") or 60)

        if mode == "create":
            selected = pending.get("selected_markets") or []
            target_chat_id = pending.get("target_chat_id")
            owner_id = query.from_user.id
            if not target_chat_id:
                await query.answer("Chat not selected.", show_alert=True)
                return
            success = await _create_widget(context, owner_id, int(target_chat_id), selected, interval_seconds)
            context.user_data.pop("widget_pending", None)
            if success:
                await query.edit_message_text(
                    "✅ Widget created. You can manage it from the widget menu.",
                    reply_markup=build_widget_menu_keyboard(),
                )
            else:
                await query.edit_message_text(
                    "❌ Widget creation failed. Please try again from the widget menu.",
                    reply_markup=build_widget_menu_keyboard(),
                )
            return
        if mode == "edit_interval":
            widget_id = pending.get("widget_id")
            if not widget_id:
                await query.answer("Widget not found.", show_alert=True)
                return
            db.update_widget_interval(int(widget_id), interval_seconds)
            db.mark_widget_dirty(int(widget_id))
            context.user_data.pop("widget_pending", None)
            await query.edit_message_text(
                "✅ Interval updated.",
                reply_markup=build_widget_menu_keyboard(),
            )
            return

    if data.startswith(CB_WIDGET_MANAGE_PREFIX):
        widget_id_str = data.replace(CB_WIDGET_MANAGE_PREFIX, "").strip()
        try:
            widget_id = int(widget_id_str)
        except ValueError:
            await query.answer("Invalid widget.", show_alert=True)
            return

        widget = db.get_widget_by_id(widget_id)
        if not widget or widget.get("owner_user_id") != query.from_user.id:
            await query.answer("Widget not found.", show_alert=True)
            return

        chat_title = widget.get("chat_title") or str(widget.get("target_chat_id"))
        markets_count = len(widget.get("selected_market_ids") or [])
        interval_label = _format_interval(int(widget.get("interval_seconds") or 0))
        status = "Enabled" if widget.get("enabled") else "Paused"
        compact_status = "ON" if widget.get("compact_mode", True) else "OFF"

        text = (
            f"Widget #{widget_id}\n"
            f"Chat: {chat_title}\n"
            f"Markets: {markets_count}\n"
            f"Interval: {interval_label}\n"
            f"Status: {status}\n"
            f"Compact view: {compact_status}"
        )
        await query.edit_message_text(text, reply_markup=build_widget_actions_keyboard(widget))
        return

    if data.startswith(CB_WIDGET_ACTION_PREFIX):
        parts = data.replace(CB_WIDGET_ACTION_PREFIX, "").split(":", 1)
        if len(parts) != 2:
            await query.answer("Invalid action.", show_alert=True)
            return
        action, widget_id_str = parts
        try:
            widget_id = int(widget_id_str)
        except ValueError:
            await query.answer("Invalid widget.", show_alert=True)
            return

        widget = db.get_widget_by_id(widget_id)
        if not widget or widget.get("owner_user_id") != query.from_user.id:
            await query.answer("Widget not found.", show_alert=True)
            return

        if action == "pause":
            db.set_widget_enabled(widget_id, False)
            await query.edit_message_text(
                "⏸ Widget paused.",
                reply_markup=build_widget_actions_keyboard({**widget, "enabled": False}),
            )
            return

        if action == "resume":
            db.set_widget_enabled(widget_id, True)
            db.mark_widget_dirty(widget_id)
            await query.edit_message_text(
                "▶️ Widget resumed.",
                reply_markup=build_widget_actions_keyboard({**widget, "enabled": True}),
            )
            return

        if action == "edit_markets":
            pending = {
                "step": "select_markets",
                "mode": "edit_markets",
                "widget_id": widget_id,
                "selected_markets": widget.get("selected_market_ids") or [],
                "market_view": "popular",
            }
            context.user_data["widget_pending"] = pending
            await query.edit_message_text(
                "Select markets to display (1–5).",
                reply_markup=build_market_selection_keyboard(
                    pending["selected_markets"], _market_view_aliases(pending)
                ),
            )
            pending["selection_message_id"] = query.message.message_id
            pending["selection_chat_id"] = query.message.chat_id
            return

        if action == "edit_interval":
            pending = {
                "step": "select_interval",
                "mode": "edit_interval",
                "widget_id": widget_id,
                "interval_seconds": widget.get("interval_seconds") or 60,
            }
            context.user_data["widget_pending"] = pending
            await query.edit_message_text(
                "Choose update interval:\nWe update only if values changed to respect Telegram limits.",
                reply_markup=build_interval_keyboard(
                    int(pending["interval_seconds"]), "✅ Save interval"
                ),
            )
            return

        if action == "toggle_compact":
            compact_mode = not bool(widget.get("compact_mode", True))
            db.set_widget_compact_mode(widget_id, compact_mode)
            db.mark_widget_dirty(widget_id)
            updated = {**widget, "compact_mode": compact_mode}
            status_label = "ON" if compact_mode else "OFF"
            await query.edit_message_text(
                f"✅ Compact view set to {status_label}.",
                reply_markup=build_widget_actions_keyboard(updated),
            )
            return

        if action == "refresh":
            result = await update_widget_message(context.bot, widget, db, force=False)
            status = result.get("status")
            if status == "updated":
                await query.answer("Widget refreshed.")
                return
            if status == "skipped" and result.get("reason") == "throttled":
                retry_in = int(result.get("retry_in") or 0)
                await query.answer(f"Too soon. Try again in {retry_in}s.", show_alert=True)
                return
            if status == "skipped" and result.get("reason") == "unchanged":
                await query.answer("No changes yet.", show_alert=True)
                return
            if status == "permission_error":
                db.set_widget_enabled(widget_id, False)
                await query.answer("Permissions error. Check bot admin rights.", show_alert=True)
                return
            await query.answer("Unable to refresh right now.", show_alert=True)
            return

        if action == "delete":
            db.delete_widget(widget_id)
            await query.edit_message_text(
                "🗑 Widget deleted.",
                reply_markup=build_widget_menu_keyboard(),
            )
            return


async def widget_pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    record_chat_from_update(update)
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await message.reply_text("Use /widget in DM to manage widgets.")
        return

    widget = db.get_widget_by_chat(chat.id)
    if not widget:
        await message.reply_text("No widget found for this chat.")
        return

    if widget.get("owner_user_id") != update.effective_user.id:
        await message.reply_text("Only the widget owner can pause this widget.")
        return

    db.set_widget_enabled(int(widget.get("widget_id")), False)
    await message.reply_text("⏸ Widget paused for this chat.")


async def widget_resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    record_chat_from_update(update)
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await message.reply_text("Use /widget in DM to manage widgets.")
        return

    widget = db.get_widget_by_chat(chat.id)
    if not widget:
        await message.reply_text("No widget found for this chat.")
        return

    if widget.get("owner_user_id") != update.effective_user.id:
        await message.reply_text("Only the widget owner can resume this widget.")
        return

    db.set_widget_enabled(int(widget.get("widget_id")), True)
    db.mark_widget_dirty(int(widget.get("widget_id")))
    await message.reply_text("▶️ Widget resumed for this chat.")

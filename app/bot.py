import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from opinion_client import get_simple_markets, get_opinion_binary_prices
from polymarket_client import get_simple_poly_markets, get_polymarket_binary_prices

# NEW: trading helper with builder attribution
from polymarket_trader import place_yes_market_order

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Help Text
HELP_TEXT = (
    "OpiPoliX Bot — crypto prediction market spread tracker.\n\n"
    "Commands:\n"
    "/start – show menu and buttons\n"
    "/help – show this help\n"
    "/about – info about this bot\n"
    "/o_markets – show active Opinion markets\n"
    "/p_markets – show active Polymarket markets\n"
    "/spread <alias> – spread check (metamask / base)\n"
    "/poly_buy <alias> <amount> – test Polymarket BUY YES via builder\n\n"
    "Examples:\n"
    "/spread metamask\n"
    "/spread base\n"
    "/poly_buy metamask 10\n"
)

# Common markets
COMMON_MARKETS = [
    {
        "alias": "metamask",
        "opinion_id": 793,
        "polymarket_id": 604067,
        "title": "MetaMask token 2025",
    },
    {
        "alias": "base",
        "opinion_id": 1270,
        "polymarket_id": 598930,
        "title": "Base token 2025",
    },
]

# Button labels (English)
BTN_SPREAD_METAMASK = "MetaMask Spread"
BTN_SPREAD_BASE = "Base Spread"
BTN_OPINION = "Opinion Markets"
BTN_POLY = "Polymarket Markets"
BTN_ABOUT = "About Bot"
BTN_TRADING = "Trading (soon)"


def build_main_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(BTN_SPREAD_METAMASK), KeyboardButton(BTN_SPREAD_BASE)],
        [KeyboardButton(BTN_OPINION), KeyboardButton(BTN_POLY)],
        [KeyboardButton(BTN_ABOUT), KeyboardButton(BTN_TRADING)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, reply_markup=build_main_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, reply_markup=build_main_keyboard())


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 *OpiPoliX Bot*\n\n"
        "Designed to track spreads on hype token launch prediction markets "
        "across *Opinion* and *Polymarket*.\n\n"
        "💡 Why?\n"
        "Instead of scrolling X (Twitter) and dozens of websites — quickly check "
        "real-time market sentiment directly in Telegram.\n\n"
        "📊 Current features:\n"
        "• Show active markets from Opinion & Polymarket\n"
        "• Spread analysis for MetaMask & Base token launch markets\n\n"
        "🚀 Roadmap:\n"
        "• Add more trending token launch markets\n"
        "• Enable real trading via bot (using API)\n"
        "• Attribute trades using our builder profile for leaderboard visibility\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Pong ✅")


async def o_markets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Fetching Opinion markets...")
    try:
        markets = get_simple_markets(5)
        if not markets:
            return await update.message.reply_text("⚠ No markets found.")
        lines = ["Opinion Markets:\n"] + [
            f"- {m['id']} — {m['title'][:60]}..." for m in markets
        ]
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"❌ Error (Opinion): {e}")


async def p_markets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Fetching Polymarket markets...")
    try:
        markets = get_simple_poly_markets(5)
        if not markets:
            return await update.message.reply_text("⚠ No markets found.")
        lines = ["Polymarket Markets:\n"] + [
            f"- {m['id']} — {m['title'][:60]}..." for m in markets
        ]
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"❌ Error (Polymarket): {e}")


async def _spread_for_alias(update: Update, context: ContextTypes.DEFAULT_TYPE, alias: str) -> None:
    alias = alias.lower()
    market = next((m for m in COMMON_MARKETS if m["alias"] == alias), None)
    if not market:
        return await update.message.reply_text(
            f"🚫 Unknown market alias '{alias}'.\n"
            f"Available: {', '.join(m['alias'] for m in COMMON_MARKETS)}"
        )

    await update.message.reply_text(f"⏳ Checking spread for '{alias}'...")

    # Opinion
    try:
        op_prices = get_opinion_binary_prices(market["opinion_id"])
        op_error = None
    except Exception as e:
        op_prices = {"yes": None, "no": None}
        op_error = str(e)

    # Polymarket
    try:
        poly_prices = get_polymarket_binary_prices(market["polymarket_id"])
        poly_error = None
    except Exception as e:
        poly_prices = {"yes": None, "no": None}
        poly_error = str(e)

    lines = [
        f"🧠 Spread for '{alias}' ({market['title']})\n",
        "Opinion:",
        f"  YES: {op_prices['yes'] if op_prices['yes'] is not None else 'N/A'}",
        f"  NO : {op_prices['no'] if op_prices['no'] is not None else 'N/A'}",
        "",
        "Polymarket:",
        f"  YES: {poly_prices['yes'] if poly_prices['yes'] is not None else 'N/A'}",
        f"  NO : {poly_prices['no'] if poly_prices['no'] is not None else 'N/A'}",
    ]

    # Spread calculation
    if op_prices["yes"] is not None and poly_prices["yes"] is not None:
        lines.append(f"Δ YES (Opinion - Polymarket): {op_prices['yes'] - poly_prices['yes']:.4f}")
    if op_prices["no"] is not None and poly_prices["no"] is not None:
        lines.append(f"Δ NO  (Opinion - Polymarket): {op_prices['no'] - poly_prices['no']:.4f}")

    # Errors if exist
    if op_error or poly_error:
        lines.extend(["", "⚠ Debug info:"])
        if op_error:
            lines.append(f"  Opinion error: {op_error}")
        if poly_error:
            lines.append(f"  Polymarket error: {poly_error}")

    await update.message.reply_text("\n".join(lines))


async def spread(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return await update.message.reply_text(
            "⚠ Usage: /spread <alias>\nExamples:\n/spread metamask\n/spread base"
        )
    await _spread_for_alias(update, context, context.args[0])


# NEW: simple trading command for YES via builder-attributed CLOB
async def poly_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /poly_buy <alias> <amount_usdc>
    Example: /poly_buy metamask 10
    """
    if len(context.args) < 2:
        return await update.message.reply_text(
            "Usage: /poly_buy <alias> <amount_usdc>\n"
            "Examples:\n"
            "/poly_buy metamask 10\n"
            "/poly_buy base 5"
        )

    alias = context.args[0].lower()
    try:
        amount = float(context.args[1])
    except ValueError:
        return await update.message.reply_text("Amount must be a number, e.g. 10")

    await update.message.reply_text(
        f"💸 Sending Polymarket BUY YES order via builder\n"
        f"Market: {alias}\n"
        f"Size: ~${amount:.2f}"
    )

    try:
        resp = place_yes_market_order(alias, amount)
        await update.message.reply_text(f"✅ Order sent.\nResponse:\n{resp}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error placing order: {e}")


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if text == BTN_SPREAD_METAMASK:
        return await _spread_for_alias(update, context, "metamask")
    if text == BTN_SPREAD_BASE:
        return await _spread_for_alias(update, context, "base")
    if text == BTN_OPINION:
        return await o_markets(update, context)
    if text == BTN_POLY:
        return await p_markets(update, context)
    if text == BTN_ABOUT:
        return await about(update, context)
    if text == BTN_TRADING:
        return await update.message.reply_text(
            "💸 Trading mode is under development.\n"
            "Soon you'll be able to execute orders directly from Telegram."
        )
    await update.message.reply_text("Unknown command. Use /help or keyboard buttons.")


def main():
    if not TOKEN:
        raise SystemExit("Set TELEGRAM_TOKEN env var first.")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("o_markets", o_markets))
    app.add_handler(CommandHandler("p_markets", p_markets))
    app.add_handler(CommandHandler("spread", spread))
    app.add_handler(CommandHandler("poly_buy", poly_buy))  # NEW
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.run_polling()


if __name__ == "__main__":
    main()

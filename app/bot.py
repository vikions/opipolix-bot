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


from wallet_manager import WalletManager
from balance_checker import check_user_balance
from withdraw_manager import withdraw_usdc_from_safe
from market_config import get_market, get_all_markets, is_market_ready
from clob_trading import trade_market
from balance_checker import BalanceChecker


from auto_trade_handlers import (
    build_auto_trade_keyboard,
    handle_auto_buy_yes_pump,
    handle_auto_buy_no_pump,
    handle_auto_buy_no_dump,
    handle_pending_auto_trade_input,
    handle_my_active_orders
)
from cancel_order_handler import cancel_auto_order

TOKEN = os.environ.get("TELEGRAM_TOKEN")


wallet_manager = WalletManager()


HELP_TEXT = (
    "OpiPoliX Bot — crypto prediction market spread tracker.\n\n"
    "Commands:\n"
    "/start – show menu and buttons\n"
    "/help – show this help\n"
    "/about – info about this bot\n"
    "/o_markets – show active Opinion markets\n"
    "/p_markets – show active Polymarket markets\n"
    "/spread <alias> – spread check (metamask / base)\n"
    "/wallet – show your trading wallet\n"
    "/balance – check your balance\n"
    "/deploy_safe – deploy Safe wallet (if not done automatically)\n\n"
    "Examples:\n"
    "/spread metamask\n"
    "/spread base\n"
)


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


BTN_SPREAD_METAMASK = "MetaMask Spread"
BTN_SPREAD_BASE = "Base Spread"
BTN_OPINION = "Opinion Markets"
BTN_POLY = "Polymarket Markets"
BTN_ABOUT = "About Bot"
BTN_TRADING = "Trading"
BTN_DEPLOY_SAFE = "🦺 Deploy Safe Wallet"


# ===== HELPER FUNCTION =====
def format_tx_hash(tx_hash):
    """Safely format transaction hash"""
    if tx_hash and tx_hash != "None" and str(tx_hash) != "None":
        tx_str = str(tx_hash)
        if len(tx_str) > 16:
            return f"`{tx_str[:16]}...`"
        return f"`{tx_str}`"
    return "`—`"


def build_main_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(BTN_SPREAD_METAMASK), KeyboardButton(BTN_SPREAD_BASE)],
        [KeyboardButton(BTN_OPINION), KeyboardButton(BTN_POLY)],
        [KeyboardButton(BTN_ABOUT), KeyboardButton(BTN_TRADING)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_trading_keyboard(safe_deployed: bool) -> ReplyKeyboardMarkup:
    """Build keyboard for Trading menu"""
    if safe_deployed:
        # Safe already deployed - show main buttons only
        rows = [
            [KeyboardButton("💰 Check Balance"), KeyboardButton("💸 Withdraw")],
            [KeyboardButton("🎯 Markets"), KeyboardButton("📋 Wallet Info")],
            [KeyboardButton("🔙 Back to Main Menu")],
        ]
    else:
        # Safe not deployed - show deploy button
        rows = [
            [KeyboardButton(BTN_DEPLOY_SAFE)],
            [KeyboardButton("🔙 Back to Main Menu")],
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_markets_keyboard() -> ReplyKeyboardMarkup:
    """Build keyboard for market selection"""
    rows = [
        [KeyboardButton("🦊 MetaMask Token"), KeyboardButton("🔵 Base Token")],
        [KeyboardButton("🎨 Abstract Token"), KeyboardButton("🧬 Extended Token")],
        [KeyboardButton("🔙 Back to Trading")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_trade_keyboard(market_alias: str) -> ReplyKeyboardMarkup:
    """Build keyboard for trading a specific market"""
    rows = [
        [KeyboardButton(f"📈 Buy YES"), KeyboardButton(f"📉 Buy NO")],
        [KeyboardButton(f"📊 Sell YES"), KeyboardButton(f"📊 Sell NO")],
        [KeyboardButton("🤖 Auto-Trade"), KeyboardButton("📊 Market Info")],
        [KeyboardButton("🔙 Back to Markets")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def build_sell_percentage_keyboard() -> ReplyKeyboardMarkup:
    """Build keyboard for selecting sell percentage"""
    rows = [
        [KeyboardButton("25%"), KeyboardButton("50%")],
        [KeyboardButton("75%"), KeyboardButton("100%")],
        [KeyboardButton("🔙 Back to Market")],
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
        "• Spread analysis for MetaMask & Base token launch markets\n"
        "• Create trading wallets with builder attribution\n"
        "• Gasless Safe wallet deployment via Polymarket Relayer\n\n"
        "🚀 Roadmap:\n"
        "• Add more trending token launch markets\n"
        "• Enable real trading via bot (using API)\n"
        "• Automatic orders on price movements\n"
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


# ===== TRADING WALLET FUNCTIONS =====

async def trading_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main Trading menu - wallet creation/display
    With AUTOMATIC Safe deployment!
    """
    telegram_id = update.message.from_user.id
    
    # Check if user has a wallet
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if wallet is None:
        # ===== NEW USER - CREATE WALLET =====
        await update.message.reply_text(
            "🔄 Creating your wallet...\n"
            "This may take a few seconds..."
        )
        
        try:
            # 1. Create EOA wallet
            wallet = wallet_manager.create_wallet_for_user(telegram_id)
            
            await update.message.reply_text(
                "✅ EOA Wallet created!\n\n"
                "🚀 Now deploying Safe wallet...\n"
                "⏳ This may take 30-60 seconds\n"
                "💰 Polymarket pays all gas fees!",
                parse_mode="Markdown"
            )
            
            # 2. AUTOMATICALLY deploy Safe
            result = wallet_manager.deploy_safe_and_setup(telegram_id)
            
            if result['status'] == 'success':
                # Success! Format transaction list
                tx_lines = []
                if result.get('safe_tx_hash'):
                    tx_lines.append(f"• Safe deploy: {format_tx_hash(result['safe_tx_hash'])}")
                if result.get('usdc_tx_hash'):
                    tx_lines.append(f"• USDC approve: {format_tx_hash(result['usdc_tx_hash'])}")
                if result.get('ctf_tx_hash'):
                    tx_lines.append(f"• CTF approve: {format_tx_hash(result['ctf_tx_hash'])}")
                
                tx_text = "\n".join(tx_lines) if tx_lines else "All transactions completed"
                
                await update.message.reply_text(
                    "🎉 *Wallet Setup Complete!*\n\n"
                    f"🦺 *Your Safe Address:*\n`{result['safe_address']}`\n\n"
                    f"📝 Transactions:\n{tx_text}\n\n"
                    f"✅ *Ready to trade!*\n\n"
                    f"💰 *Next Steps:*\n"
                    f"1️⃣ Send USDC to your Safe address (copy above)\n"
                    f"2️⃣ Use /balance to check your deposit\n"
                    f"3️⃣ Go to Markets and start trading!\n\n"
                    f"⚠️ *IMPORTANT:*\n"
                    f"• Only send USDC on *Polygon network*\n"
                    f"• USDC Contract: `0x2791...4174`\n"
                    f"• Minimum: $1 USDC per trade\n\n"
                    f"👉 Press 🎯 Markets to start!",
                    parse_mode="Markdown",
                    reply_markup=build_trading_keyboard(True)
                )
            else:
                # Deploy error - but EOA created
                await update.message.reply_text(
                    f"⚠️ Safe deployment failed\n\n"
                    f"Error: {result.get('error', 'Unknown')}\n\n"
                    f"Your EOA wallet is created, but Safe deployment failed.\n"
                    f"You can try again with the button below.",
                    reply_markup=build_trading_keyboard(False)
                )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error creating wallet: {e}\n\n"
                "Please try again or contact support.",
                reply_markup=build_main_keyboard()
            )
            return
    
    else:
        # ===== EXISTING USER =====
        # RELOAD wallet from DB to get current safe_address
        wallet = wallet_manager.get_wallet(telegram_id)
        
        if wallet['safe_address']:
            # Safe deployed
            await update.message.reply_text(
                "💼 *Your Trading Wallet*\n\n"
                f"🦺 *Safe Address:*\n`{wallet['safe_address']}`\n\n"
                f"💰 *To deposit USDC:*\n"
                f"1️⃣ Send USDC (Polygon) to your Safe address above\n"
                f"2️⃣ Use /balance to check your balance\n"
                f"3️⃣ Start trading!\n\n"
                f"⚠️ *IMPORTANT:* Only send USDC on *Polygon network*!\n"
                f"Contract: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`\n\n"
                f"✅ Ready to trade!\n\n"
                f"💡 Available commands:\n"
                f"• /balance - Check balance\n"
                f"• /withdraw - Withdraw funds\n"
                f"• /spread <market> - Check spreads",
                parse_mode="Markdown",
                reply_markup=build_trading_keyboard(True)
            )
        else:
            # EOA exists, but Safe not deployed
            await update.message.reply_text(
                "💼 *Your Wallet Info*\n\n"
                f"🦺 Safe Wallet: Not deployed yet\n\n"
                f"Use the button below to deploy your Safe wallet\n"
                f"💰 Deployment is FREE (Polymarket pays gas)",
                parse_mode="Markdown",
                reply_markup=build_trading_keyboard(False)
            )


async def deploy_safe_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
   
    telegram_id = update.message.from_user.id
    
    
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if not wallet:
        await update.message.reply_text(
            "❌ You don't have a wallet yet!\n"
            "Press 'Trading' button to create one first.",
            reply_markup=build_main_keyboard()
        )
        return
    
    
    if wallet['safe_address']:
        await update.message.reply_text(
            f"✅ Your Safe is already deployed!\n\n"
            f"🦺 Safe Address:\n`{wallet['safe_address']}`\n\n"
            f"You're ready to trade!",
            parse_mode="Markdown",
            reply_markup=build_trading_keyboard(True)
        )
        return
    
    
    await update.message.reply_text(
        "🚀 Deploying your Safe wallet...\n\n"
        "⏳ This may take 30-60 seconds\n"
        "💰 Polymarket pays for gas!\n"
        "🎯 With builder attribution!\n\n"
        "Please wait..."
    )
    
    try:
        
        result = wallet_manager.deploy_safe_and_setup(telegram_id)
        
        if result['status'] == 'success':
            
            tx_lines = []
            if result.get('safe_tx_hash'):
                tx_lines.append(f"• Safe deploy: {format_tx_hash(result['safe_tx_hash'])}")
            if result.get('usdc_tx_hash'):
                tx_lines.append(f"• USDC approve: {format_tx_hash(result['usdc_tx_hash'])}")
            if result.get('ctf_tx_hash'):
                tx_lines.append(f"• CTF approve: {format_tx_hash(result['ctf_tx_hash'])}")
            
            tx_text = "\n".join(tx_lines) if tx_lines else "All transactions completed"
            
            await update.message.reply_text(
                "🎉 *Safe Deployed Successfully!*\n\n"
                f"🦺 Safe Address:\n`{result['safe_address']}`\n\n"
                f"📝 Transactions:\n{tx_text}\n\n"
                f"💰 All gas paid by Polymarket!\n"
                f"🎯 Trades attributed to OpiPoliX!\n\n"
                f"✅ You're ready to trade!",
                parse_mode="Markdown",
                reply_markup=build_trading_keyboard(True)
            )
        else:
            
            error_msg = result.get('error', 'Unknown error')
            step = result.get('step', 'unknown')
            
            await update.message.reply_text(
                f"❌ Deployment failed at: {step}\n\n"
                f"Error: {error_msg}\n\n"
                f"Please try again in a few minutes.\n"
                f"If the problem persists, contact support.",
                reply_markup=build_trading_keyboard(False)
            )
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error deploying Safe: {str(e)}\n\n"
            f"Please try again or contact support.",
            reply_markup=build_trading_keyboard(False)
        )


async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Check user's balance
    """
    telegram_id = update.message.from_user.id
    
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if not wallet:
        await update.message.reply_text(
            "❌ You don't have a wallet yet!\n"
            "Press 'Trading' button to create one.",
            reply_markup=build_main_keyboard()
        )
        return
    
    # Show loading message
    await update.message.reply_text("🔍 Checking your balance...")
    
    try:
        # Check balance via Web3
        balance_message = check_user_balance(
            eoa_address=wallet['eoa_address'],
            safe_address=wallet.get('safe_address')
        )
        
        await update.message.reply_text(
            balance_message,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error checking balance: {str(e)}\n\n"
            "Please make sure you have internet connection and try again."
        )


async def withdraw_funds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Withdraw USDC from Safe
    """
    telegram_id = update.message.from_user.id
    
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if not wallet or not wallet['safe_address']:
        await update.message.reply_text(
            "❌ You don't have a Safe wallet yet!\n"
            "Deploy Safe wallet first.",
            reply_markup=build_main_keyboard()
        )
        return
    
    # Withdrawal instructions
    await update.message.reply_text(
        "💸 *Withdraw USDC*\n\n"
        "To withdraw, send a message in format:\n"
        "`/withdraw <amount> <address>`\n\n"
        "Examples:\n"
        "`/withdraw 10 0x742d...5aB2`\n"
        "`/withdraw 5.5 0x742d...5aB2`\n\n"
        "⚠️ Make sure you have enough USDC in your Safe!",
        parse_mode="Markdown"
    )


async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /withdraw <amount> <address>
    """
    telegram_id = update.message.from_user.id
    
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if not wallet or not wallet['safe_address']:
        await update.message.reply_text(
            "❌ You don't have a Safe wallet yet!",
            reply_markup=build_main_keyboard()
        )
        return
    
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Usage: /withdraw <amount> <address>\n\n"
            "Examples:\n"
            "`/withdraw 10 0x742d...5aB2`\n"
            "`/withdraw 5.5 0x742d...5aB2`",
            parse_mode="Markdown"
        )
        return
    
    try:
        
        amount = float(context.args[0])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive!")
            return
        
        
        recipient = context.args[1]
        
        
        if not recipient.startswith('0x') or len(recipient) != 42:
            await update.message.reply_text("❌ Invalid address format!")
            return
        
        await update.message.reply_text(
            f"💸 Withdrawing {amount} USDC...\n\n"
            f"To: `{recipient}`\n\n"
            "⏳ Please wait...",
            parse_mode="Markdown"
        )
        
        
        private_key = wallet_manager.get_private_key(telegram_id)
        
        
        result = withdraw_usdc_from_safe(
            user_private_key=private_key,
            recipient_address=recipient,
            amount_usdc=amount,
            telegram_id=telegram_id
        )
        
        if result['status'] == 'success':
            await update.message.reply_text(
                f"✅ *Withdrawal Successful!*\n\n"
                f"💰 Amount: {amount} USDC\n"
                f"📍 To: `{recipient}`\n\n"
                f"📝 Transaction: `{result['tx_hash'][:16]}...`\n\n"
                f"🔗 [View on PolygonScan](https://polygonscan.com/tx/{result['tx_hash']})",
                parse_mode="Markdown"
            )
        else:
            error_msg = result.get('error', 'Unknown error')
            await update.message.reply_text(
                f"❌ Withdrawal failed\n\n"
                f"Error: {error_msg}"
            )
            
    except ValueError:
        await update.message.reply_text("❌ Invalid amount format! Use numbers like: 10 or 5.5")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            "Please try again or contact support."
        )


async def markets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Меню выбора маркета для торговли
    """
    telegram_id = update.message.from_user.id
    
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if not wallet or not wallet['safe_address']:
        await update.message.reply_text(
            "❌ You need a Safe wallet to trade!\n"
            "Deploy Safe wallet first.",
            reply_markup=build_main_keyboard()
        )
        return
    
   
    await update.message.reply_text(
        "🎯 *Available Markets*\n\n"
        "🦊 *MetaMask Token by June 30*\n"
        "Will MetaMask launch a token by June 30?\n\n"
        "🔵 *Base Token 2025*\n"
        "Will Base launch a token in 2025?\n\n"
        "🎨 *Abstract Token by Dec 31, 2026*\n"
        "Will Abstract launch a token by December 31, 2026?\n\n"
        "🧬 *Extended Token by March 31, 2026*\n"
        "Will Extended launch a token by March 31, 2026?\n\n"
        "Select a market to trade:",
        parse_mode="Markdown",
        reply_markup=build_markets_keyboard()
    )


async def market_trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, market_alias: str) -> None:
    """
    Меню торговли конкретным маркетом
    """
    telegram_id = update.message.from_user.id
    
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if not wallet or not wallet['safe_address']:
        await update.message.reply_text(
            "❌ You need a Safe wallet to trade!",
            reply_markup=build_main_keyboard()
        )
        return
    
    
    if not is_market_ready(market_alias):
        await update.message.reply_text(
            f"⚠️ {market_alias.title()} market is not ready yet!\n"
            "Coming soon...",
            reply_markup=build_markets_keyboard()
        )
        return
    
    market = get_market(market_alias)
    
    
    await update.message.reply_text(
        f"{market['emoji']} *{market['title']}*\n\n"
        f"📊 Choose your action:\n\n"
        f"📈 *Buy YES* - Buy shares that it will happen\n"
        f"📉 *Buy NO* - Buy shares that it won't happen\n"
        f"📊 *Sell* - Sell your existing shares\n\n"
        f"💡 Trades are executed at market price\n"
        f"⚡ All transactions are gasless!",
        parse_mode="Markdown",
        reply_markup=build_trade_keyboard(market_alias)
    )
    
    
    context.user_data['current_market'] = market_alias


async def execute_trade(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: float) -> None:
    """
    Выполнить трейд
    """
    telegram_id = update.message.from_user.id
    trade_info = context.user_data.get('pending_trade')
    
    if not trade_info:
        await update.message.reply_text("❌ Trade info not found")
        return
    
    market_alias = trade_info['market']
    action = trade_info['action']  # 'buy' or 'sell'
    outcome = trade_info['outcome']  # 'yes' or 'no'
    
    market = get_market(market_alias)
    token_id = market['tokens'][outcome]
    
    
    wallet = wallet_manager.get_wallet(telegram_id)
    
    if not wallet or not wallet['safe_address']:
        await update.message.reply_text(
            "❌ You need a Safe wallet to trade!",
            reply_markup=build_main_keyboard()
        )
        return
    
    
    action_emoji = "📈" if action == "buy" else "📊"
    action_text = "Buying" if action == "buy" else "Selling"
    
    await update.message.reply_text(
        f"{action_emoji} {action_text} {outcome.upper()} shares...\n\n"
        f"💰 Amount: ${amount} USDC\n"
        f"{market['emoji']} {market['title']}\n\n"
        f"⏳ Please wait..."
    )
    
    try:
        
        private_key = wallet_manager.get_private_key(telegram_id)
        
        
        side = "BUY" if action == "buy" else "SELL"
        
        result = trade_market(
            user_private_key=private_key,
            token_id=token_id,
            side=side,
            amount_usdc=amount,
            telegram_id=telegram_id,
            funder_address=wallet["safe_address"],  
        )

        
        if result['status'] == 'success':
            await update.message.reply_text(
                f"✅ *Trade Successful!*\n\n"
                f"{action_emoji} {action_text} {outcome.upper()}\n"
                f"💰 Amount: ${result['amount']} USDC\n\n"
                f"🎯 Order ID: `{result['order_id'][:16]}...`\n\n"
                f"⚡ Gasless transaction!\n"
                f"🏆 OpiPoliX!",
                parse_mode="Markdown",
                reply_markup=build_trade_keyboard(market_alias)
            )
        else:
            error_msg = result.get('error', 'Unknown error')
            await update.message.reply_text(
                f"❌ Trade failed\n\n"
                f"Error: {error_msg}\n\n"
                f"Please try again.",
                reply_markup=build_trade_keyboard(market_alias)
            )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            f"Please try again or contact support.",
            reply_markup=build_trade_keyboard(market_alias)
        )
    
    finally:
        
        context.user_data.pop('pending_trade', None)


async def auto_trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, market_alias: str):
    """Меню Auto-Trade с описанием"""
    market = get_market(market_alias)
    
    await update.message.reply_text(
        f"🤖 *Auto-Trade*\n"
        f"{market['emoji']} {market['title']}\n\n"
        f"💡 *Why use Auto-Trade?*\n\n"
        f"When hyped tokens get listed, prices can:\n"
        f"• 🚀 Pump +50-100% in minutes (real news)\n"
        f"• 📉 Dump -30-50% quickly (fake news)\n\n"
        f"🎯 *Protect yourself with triggers:*\n\n"
        f"📈 *Auto-Buy on Pump*\n"
        f"Buy YES automatically when price jumps\n"
        f"Example: Buy $10 when price hits +10%\n\n"
        f"📉 *Auto-Sell on Dump*\n"
        f"Sell YES automatically when price drops\n"
        f"Example: Sell if price drops -15%\n\n"
        f"⚡ *Benefits:*\n"
        f"• No need to watch prices 24/7\n"
        f"• React instantly to market moves\n"
        f"• Set & forget protection\n"
        f"• Still gasless!\n\n"
        f"👉 Choose your trigger type:",
        parse_mode="Markdown",
        reply_markup=build_auto_trade_keyboard(market_alias)
    )
    
    
    context.user_data['auto_trade_market'] = market_alias




async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок"""
    text = update.message.text.strip()
    
    
    if text.startswith('/'):
        return
    
    
    if await handle_pending_auto_trade_input(update, context, text):
        return
    
    
    if context.user_data.get('pending_trade'):
        try:
            amount = float(text)
            
            if amount < 1:
                await update.message.reply_text("❌ Minimum amount is $1 USDC")
                return
            
            
            return await execute_trade(update, context, amount)
            
        except ValueError:
            
            pass
    
    
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
        return await trading_menu(update, context)
    
    
    if text == BTN_DEPLOY_SAFE:
        return await deploy_safe_wallet(update, context)
    
    if text == "💰 Check Balance":
        return await check_balance(update, context)
    
    if text == "💸 Withdraw":
        return await withdraw_funds(update, context)
    
    if text == "🎯 Markets":
        return await markets_menu(update, context)
    
    if text == "📋 Wallet Info":
        telegram_id = update.message.from_user.id
        wallet = wallet_manager.get_wallet(telegram_id)
        
        if not wallet or not wallet['safe_address']:
            await update.message.reply_text(
                "❌ You don't have a Safe wallet yet!",
                reply_markup=build_main_keyboard()
            )
            return
        
        await update.message.reply_text(
            "💼 *Your Trading Wallet*\n\n"
            f"🦺 *Safe Address:*\n`{wallet['safe_address']}`\n\n"
            f"💰 *How to Deposit USDC:*\n"
            f"1️⃣ Copy your Safe address above\n"
            f"2️⃣ Send USDC from exchange/wallet to this address\n"
            f"3️⃣ Select *Polygon* network (NOT Ethereum!)\n"
            f"4️⃣ Wait for confirmation (~30 seconds)\n"
            f"5️⃣ Check balance with 💰 Check Balance\n\n"
            f"⚠️ *IMPORTANT - READ CAREFULLY:*\n"
            f"• Network: *Polygon* (MATIC)\n"
            f"• Token: USDC\n"
            f"• Contract: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`\n"
            f"• Sending on wrong network = *FUNDS LOST*\n\n"
            f"👉 Popular exchanges with Polygon USDC:\n"
            f"• Binance (withdraw USDC, select Polygon)\n"
            f"• Coinbase (Bridge to Polygon)\n"
            f"• Bybit (USDC Polygon)\n"
            f"• OKX (USDC Polygon)\n\n"
            f"🔗 [Verify on PolygonScan](https://polygonscan.com/address/{wallet['safe_address']})",
            parse_mode="Markdown",
            reply_markup=build_trading_keyboard(True)
        )
        return
    
    
    if text == "🦊 MetaMask Token":
        return await market_trade_menu(update, context, "metamask")
    
    if text == "🔵 Base Token":
        return await market_trade_menu(update, context, "base")
    
    if text == "🎨 Abstract Token":
        return await market_trade_menu(update, context, "abstract")
    
    if text == "🧬 Extended Token":
        return await market_trade_menu(update, context, "extended")
    
    
    if text == "🔙 Back to Trading":
        return await trading_menu(update, context)
    
    if text == "🔙 Back to Markets":
        return await markets_menu(update, context)
    
    if text == "🔙 Back to Market":
        
        current_market = context.user_data.get('auto_trade_market') or context.user_data.get('current_market')
        
        if not current_market:
            return await markets_menu(update, context)
        
        return await market_trade_menu(update, context, current_market)
    
    
    if text in ["📈 Buy YES", "📉 Buy NO", "📊 Sell YES", "📊 Sell NO"]:
        
        current_market = context.user_data.get('current_market')
        
        if not current_market:
            await update.message.reply_text(
                "❌ Please select a market first!",
                reply_markup=build_markets_keyboard()
            )
            return
        
        
        if "Buy YES" in text:
            action = "buy"
            outcome = "yes"
        elif "Buy NO" in text:
            action = "buy"
            outcome = "no"
        elif "Sell YES" in text:
            action = "sell"
            outcome = "yes"
        else:  # Sell NO
            action = "sell"
            outcome = "no"
        
        market = get_market(current_market)
        
        
        if action == "sell":
            
            context.user_data['pending_sell'] = {
                'market': current_market,
                'outcome': outcome
            }
            
            await update.message.reply_text(
                f"{market['emoji']} *{market['title']}*\n\n"
                f"📊 Sell {outcome.upper()} shares\n\n"
                f"📉 Choose percentage to sell:",
                parse_mode="Markdown",
                reply_markup=build_sell_percentage_keyboard()
            )
        else:
            
            context.user_data['pending_trade'] = {
                'market': current_market,
                'action': action,
                'outcome': outcome
            }
            
            await update.message.reply_text(
                f"{market['emoji']} *{market['title']}*\n\n"
                f"📊 Buy {outcome.upper()} shares\n\n"
                f"💰 How much USDC do you want to spend?\n"
                f"Send amount like: `10` or `5.5`\n\n"
                f"⚠️ Minimum: $1 USDC",
                parse_mode="Markdown"
            )
        return
    
    
    if text == "🤖 Auto-Trade":
        current_market = context.user_data.get('current_market')
        
        if not current_market:
            await update.message.reply_text(
                "❌ Please select a market first!",
                reply_markup=build_markets_keyboard()
            )
            return
        
        return await auto_trade_menu(update, context, current_market)
    
    
    if text in ["25%", "50%", "75%", "100%"]:
        pending_sell = context.user_data.get('pending_sell')
        
        if not pending_sell:
            await update.message.reply_text(
                "❌ No pending sell operation",
                reply_markup=build_main_keyboard()
            )
            return
        
        telegram_id = update.message.from_user.id
        wallet = wallet_manager.get_wallet(telegram_id)
        
        if not wallet or not wallet['safe_address']:
            await update.message.reply_text(
                "❌ You need a Safe wallet to trade!",
                reply_markup=build_main_keyboard()
            )
            return
        
        market_alias = pending_sell['market']
        outcome = pending_sell['outcome']
        percentage = int(text.strip('%'))
        
        market = get_market(market_alias)
        token_id = market['tokens'][outcome]
        
        await update.message.reply_text(
            f"🔍 Getting your {outcome.upper()} token balance...\n"
            f"⏳ Please wait..."
        )
        
        try:
            
            private_key = wallet_manager.get_private_key(telegram_id)
            
            
            balance_checker = BalanceChecker()
            token_balance_raw = balance_checker.get_position_balance(
                wallet['safe_address'],
                token_id
            )
            
            
            token_balance = token_balance_raw / 1e6
            
            print(f"📊 Token balance: {token_balance_raw} raw = {token_balance} tokens")
            
            if token_balance <= 0:
                await update.message.reply_text(
                    f"❌ You have no {outcome.upper()} tokens to sell!\n\n"
                    f"📊 Current balance: 0",
                    reply_markup=build_trade_keyboard(market_alias)
                )
                context.user_data.pop('pending_sell', None)
                return
            
           
            amount_to_sell = (token_balance * percentage) / 100
            
            await update.message.reply_text(
                f"📊 Selling {percentage}% of {outcome.upper()} tokens...\n\n"
                f"📉 Your balance: {token_balance:.2f} tokens\n"
                f"💰 Selling: {amount_to_sell:.2f} tokens\n\n"
                f"⏳ Please wait..."
            )
            
           
            result = trade_market(
                user_private_key=private_key,
                token_id=token_id,
                side="SELL",
                amount_usdc=amount_to_sell,  
                telegram_id=telegram_id,
                funder_address=wallet['safe_address']
            )
            
            if result['status'] == 'success':
                order_id = result.get('order_id', 'N/A')
                
                if isinstance(order_id, dict):
                    order_id = order_id.get('orderID', str(order_id)[:16])
                
                await update.message.reply_text(
                    f"✅ *Sell Successful!*\n\n"
                    f"📊 Sold {percentage}% of {outcome.upper()}\n"
                    f"💰 Amount: {amount_to_sell:.2f} tokens\n\n"
                    f"🎯 Order ID: `{str(order_id)[:16]}...`\n\n"
                    f"⚡ Gasless transaction!\n"
                    f"🏆 OpiPoliX!",
                    parse_mode="Markdown",
                    reply_markup=build_trade_keyboard(market_alias)
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                await update.message.reply_text(
                    f"❌ Sell failed\n\n"
                    f"Error: {error_msg}\n\n"
                    f"Please try again.",
                    reply_markup=build_trade_keyboard(market_alias)
                )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}\n\n"
                f"Please try again or contact support.",
                reply_markup=build_trade_keyboard(market_alias)
            )
        
        finally:
            
            context.user_data.pop('pending_sell', None)
        
        return
    
   
    if text == "📈 Buy YES on Pump":
        return await handle_auto_buy_yes_pump(update, context)
    
    if text == "🎭 Buy NO on Pump":
        return await handle_auto_buy_no_pump(update, context)
    
    if text == "📉 Buy NO on Dump":
        return await handle_auto_buy_no_dump(update, context)
    
    if text == "📊 My Active Orders":
        return await handle_my_active_orders(update, context)
    
    if text == "🔙 Back to Main Menu":
        await update.message.reply_text(
            "📱 Main Menu",
            reply_markup=build_main_keyboard()
        )
        return
    
    if text == "📊 Trade":
        await update.message.reply_text(
            "📊 Trading features coming soon!\n\n"
            "You'll be able to:\n"
            "• Place market orders\n"
            "• Set limit orders\n"
            "• Create auto-orders on price movements\n\n"
            "Stay tuned! 🚀"
        )
        return
    
   
    await update.message.reply_text(
        "Unknown command. Use /help or keyboard buttons.",
        reply_markup=build_main_keyboard()
    )

async def worker_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check Auto-Trade worker status"""
    from worker_health import get_monitor
    
    monitor = get_monitor()
    status_message = monitor.format_status()
    
    await update.message.reply_text(
        status_message,
        parse_mode="Markdown"
    )


def main():
    if not TOKEN:
        raise SystemExit("Set TELEGRAM_TOKEN env var first.")

    app = Application.builder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("o_markets", o_markets))
    app.add_handler(CommandHandler("p_markets", p_markets))
    app.add_handler(CommandHandler("spread", spread))
    
    # Wallet
    app.add_handler(CommandHandler("balance", check_balance))
    app.add_handler(CommandHandler("wallet", trading_menu))
    app.add_handler(CommandHandler("deploy_safe", deploy_safe_wallet))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    app.add_handler(CommandHandler("cancel", cancel_auto_order))
    app.add_handler(CommandHandler("worker_status", worker_status))
    
    # Text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    
    app.run_polling()


if __name__ == "__main__":
    main()
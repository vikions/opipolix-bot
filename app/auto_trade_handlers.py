"""
Auto-Trade handlers для бота
Обработка создания и управления авто-ордерами
"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from auto_trade_manager import AutoTradeManager
from market_config import get_market


# Initialize manager
auto_trade_manager = AutoTradeManager()


def build_auto_trade_keyboard(market_alias: str) -> ReplyKeyboardMarkup:
    """Клавиатура для Auto-Trade меню"""
    rows = [
        [KeyboardButton("📈 Buy YES on Pump"), KeyboardButton("🎭 Buy NO on Pump")],
        [KeyboardButton("📉 Buy NO on Dump")],
        [KeyboardButton("📊 My Active Orders")],
        [KeyboardButton("🔙 Back to Market")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def handle_auto_buy_yes_pump(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Buy YES on Pump'"""
    current_market = context.user_data.get('auto_trade_market') or context.user_data.get('current_market')
    
    if not current_market:
        await update.message.reply_text("❌ Please select a market first!")
        return
    
    # Сохраняем что юзер настраивает auto-buy YES
    context.user_data['pending_auto_trade'] = {
        'market': current_market,
        'type': 'buy_yes_pump',
        'step': 'trigger_percent'
    }
    
    market = get_market(current_market)
    
    await update.message.reply_text(
        f"📈 *Buy YES on Pump*\n"
        f"{market['emoji']} {market['title']}\n\n"
        f"🎯 *Setup trigger:*\n\n"
        f"When YES price pumps by how much %?\n\n"
        f"*Examples:*\n"
        f"• `10` - Trigger at +10% pump\n"
        f"• `25` - Trigger at +25% pump\n"
        f"• `50` - Trigger at +50% pump\n\n"
        f"💡 *Tip:* For low probability markets (1-5%), even 50% pump is common!\n\n"
        f"📝 Send trigger % (just number):",
        parse_mode="Markdown"
    )


async def handle_auto_buy_no_pump(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Buy NO on Pump' (fake news)"""
    current_market = context.user_data.get('auto_trade_market') or context.user_data.get('current_market')
    
    if not current_market:
        await update.message.reply_text("❌ Please select a market first!")
        return
    
    context.user_data['pending_auto_trade'] = {
        'market': current_market,
        'type': 'buy_no_pump',
        'step': 'trigger_percent'
    }
    
    market = get_market(current_market)
    
    await update.message.reply_text(
        f"🎭 *Buy NO on Pump (Fake News Strategy)*\n"
        f"{market['emoji']} {market['title']}\n\n"
        f"🎯 *Strategy:*\n"
        f"When YES pumps hard, buy NO betting it's fake news!\n\n"
        f"📈 When YES price pumps by how much %?\n\n"
        f"*Examples:*\n"
        f"• `20` - Buy NO when YES pumps +20%\n"
        f"• `50` - Buy NO when YES pumps +50%\n"
        f"• `100` - Buy NO when YES pumps +100%\n\n"
        f"💡 *Perfect for:* Catching fake news pumps!\n\n"
        f"📝 Send trigger % (just number):",
        parse_mode="Markdown"
    )


async def handle_auto_buy_no_dump(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Buy NO on Dump'"""
    current_market = context.user_data.get('auto_trade_market') or context.user_data.get('current_market')
    
    if not current_market:
        await update.message.reply_text("❌ Please select a market first!")
        return
    
    context.user_data['pending_auto_trade'] = {
        'market': current_market,
        'type': 'buy_no_dump',
        'step': 'trigger_percent'
    }
    
    market = get_market(current_market)
    
    await update.message.reply_text(
        f"📉 *Buy NO on Dump (Safety Strategy)*\n"
        f"{market['emoji']} {market['title']}\n\n"
        f"🎯 *Strategy:*\n"
        f"After a pump, if YES dumps = fake news confirmed!\n\n"
        f"📉 When YES price dumps by how much %?\n\n"
        f"*Examples:*\n"
        f"• `15` - Buy NO when YES dumps -15%\n"
        f"• `30` - Buy NO when YES dumps -30%\n"
        f"• `50` - Buy NO when YES dumps -50%\n\n"
        f"💡 *Perfect for:* Safety net after pump!\n\n"
        f"📝 Send trigger % (just number):",
        parse_mode="Markdown"
    )


async def handle_pending_auto_trade_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """
    Обработка ввода данных для auto-trade
    
    Returns:
        bool: True если обработали, False если нет
    """
    pending = context.user_data.get('pending_auto_trade')
    
    if not pending:
        return False
    
    step = pending['step']
    
    try:
        if step == 'trigger_percent':
            # Юзер ввёл процент триггера
            trigger_percent = float(text)
            
            if trigger_percent <= 0 or trigger_percent > 500:
                await update.message.reply_text(
                    "❌ Invalid percentage!\n"
                    "Please enter a number between 1 and 500"
                )
                return True
            
            # Сохраняем процент и переходим к вводу суммы
            pending['trigger_percent'] = trigger_percent
            pending['step'] = 'amount'
            
            await update.message.reply_text(
                f"✅ Trigger set: {trigger_percent}%\n\n"
                f"💰 How much USDC to spend?\n\n"
                f"*Examples:*\n"
                f"• `5` - Spend $5\n"
                f"• `10` - Spend $10\n"
                f"• `20` - Spend $20\n\n"
                f"⚠️ Minimum: $1 USDC\n\n"
                f"📝 Send amount:",
                parse_mode="Markdown"
            )
            return True
            
        elif step == 'amount':
            # Юзер ввёл сумму
            amount = float(text)
            
            if amount < 1:
                await update.message.reply_text("❌ Minimum amount is $1 USDC")
                return True
            
            # Создаём ордер!
            telegram_id = update.message.from_user.id
            
            order_id = auto_trade_manager.create_order(
                telegram_id=telegram_id,
                market_alias=pending['market'],
                order_type=pending['type'],
                trigger_percent=pending['trigger_percent'],
                amount_usdc=amount
            )
            
            # Форматируем результат
            market = get_market(pending['market'])
            order_type_name = {
                'buy_yes_pump': '📈 Buy YES on Pump',
                'buy_no_pump': '🎭 Buy NO on Pump (Fake News)',
                'buy_no_dump': '📉 Buy NO on Dump'
            }.get(pending['type'], 'Unknown')
            
            await update.message.reply_text(
                f"✅ *Auto-Order Created!*\n\n"
                f"{market['emoji']} *{market['title']}*\n"
                f"{order_type_name}\n\n"
                f"🎯 Trigger: {pending['trigger_percent']}%\n"
                f"💰 Amount: ${amount:.2f}\n"
                f"🆔 Order ID: `{order_id}`\n\n"
                f"🤖 Bot is now monitoring prices!\n"
                f"You'll get notified when it triggers.\n\n"
                f"📊 View all orders: My Active Orders",
                parse_mode="Markdown",
                reply_markup=build_auto_trade_keyboard(pending['market'])
            )
            
            # Очищаем pending
            context.user_data.pop('pending_auto_trade', None)
            
            return True
    
    except ValueError:
        await update.message.reply_text("❌ Please send a valid number!")
        return True
    
    return False


async def handle_my_active_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать активные ордера пользователя"""
    telegram_id = update.message.from_user.id
    
    orders = auto_trade_manager.get_user_orders(telegram_id)
    
    if not orders:
        await update.message.reply_text(
            "📊 *My Active Auto-Orders*\n\n"
            "You have no active orders yet.\n\n"
            "Create one using:\n"
            "• 📈 Buy YES on Pump\n"
            "• 🎭 Buy NO on Pump\n"
            "• 📉 Buy NO on Dump",
            parse_mode="Markdown"
        )
        return
    
    # Форматируем список ордеров
    lines = ["📊 *My Active Auto-Orders*\n"]
    
    for order in orders:
        info = auto_trade_manager.format_order_info(order)
        lines.append(info)
        lines.append("")  # Пустая строка между ордерами
    
    lines.append(f"Total: {len(orders)} active order(s)")
    lines.append("\n🔴 To cancel: Send `/cancel <order_id>`")
    lines.append("Example: `/cancel 1`")
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown"
    )

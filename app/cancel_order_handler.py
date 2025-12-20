
from telegram import Update
from telegram.ext import ContextTypes
from auto_trade_manager import AutoTradeManager

auto_trade_manager = AutoTradeManager()


async def cancel_auto_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    telegram_id = update.message.from_user.id
    
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/cancel <order_id>`\n\n"
            "Example: `/cancel 1`\n\n"
            "💡 Use `📊 My Active Orders` to see your order IDs",
            parse_mode="Markdown"
        )
        return
    
    try:
        order_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid order ID! Must be a number")
        return
    
    
    orders = auto_trade_manager.get_user_orders(telegram_id)
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        await update.message.reply_text(
            f"❌ Order #{order_id} not found!\n\n"
            f"💡 Use `📊 My Active Orders` to see your orders",
            parse_mode="Markdown"
        )
        return
    
    
    auto_trade_manager.cancel_order(order_id)
    
    await update.message.reply_text(
        f"✅ *Order Cancelled!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"📊 Type: {order['trigger_type']}\n"
        f"💰 Amount: ${order['amount']}\n\n"
        f"The order will no longer be monitored.",
        parse_mode="Markdown"
    )

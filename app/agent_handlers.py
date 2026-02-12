"""
Telegram bot handlers for TGE Agent Mode UI
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from agent_db import AgentDatabase

agent_db = AgentDatabase()


async def show_agent_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open agent menu from a regular message (ReplyKeyboard flow)"""
    keyboard = [
        [InlineKeyboardButton("➕ Create New Agent", callback_data="agent_create")],
        [InlineKeyboardButton("📋 My Agents", callback_data="agent_list")],
        [InlineKeyboardButton("📊 Decision History", callback_data="agent_history")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🤖 *TGE AGENT MODE*\n\n"
        "Autonomous agents that monitor Discord channels and trade on Polymarket using AI decision-making.\n\n"
        "*What would you like to do?*"
    )

    await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")


async def show_agent_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Use the original message to reply with inline menu
    await query.message.reply_text(
        text=(
            "🤖 *TGE AGENT MODE*\n\n"
            "Autonomous agents that monitor Discord channels and trade on Polymarket using AI decision-making.\n\n"
            "*What would you like to do?*"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create New Agent", callback_data="agent_create")],
            [InlineKeyboardButton("📋 My Agents", callback_data="agent_list")],
            [InlineKeyboardButton("📊 Decision History", callback_data="agent_history")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")],
        ]),
        parse_mode="Markdown",
    )


async def handle_create_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📊 Polymarket Discord", callback_data="agent_channel_polymarket")],
        [InlineKeyboardButton("💭 Opinion Discord", callback_data="agent_channel_opinion")],
        [InlineKeyboardButton("➕ Custom Channel (Your Test)", callback_data="agent_channel_custom")],
        [InlineKeyboardButton("🔙 Back", callback_data="agent_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text="*Step 1/4:* Select Discord channel to monitor:", reply_markup=reply_markup, parse_mode="Markdown")


async def handle_custom_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["agent_creation_step"] = "awaiting_channel_id"

    await query.edit_message_text(
        text=(
            "*Step 2/4:* Send me your Discord Channel ID\n\n"
            "How to: enable Developer Mode in Discord → Right click channel → Copy Channel ID\n\n"
            "Send the channel ID now:"
        ),
        parse_mode="Markdown",
    )


async def handle_agent_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text input during agent creation"""
    step = context.user_data.get("agent_creation_step")
    text = update.message.text.strip()
    telegram_id = update.effective_user.id

    if step == "awaiting_channel_id":
        context.user_data["agent_channel_id"] = text
        context.user_data["agent_creation_step"] = "channel_name"

        await update.message.reply_text("*Step 3/4:* Give this channel a name (for easy identification):", parse_mode="Markdown")
        return

    if step == "channel_name":
        context.user_data["agent_channel_name"] = text
        # Ask about auto-trade
        context.user_data["agent_creation_step"] = "awaiting_autotrade_choice"

        keyboard = [
            [InlineKeyboardButton("✅ YES - Auto-trade ON", callback_data="agent_autotrade_yes")],
            [InlineKeyboardButton("❌ NO - Alerts only", callback_data="agent_autotrade_no")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "*Step 4/4:* Enable automatic trading?\n\n✅ YES: Agent will execute trades automatically\n❌ NO: Agent will only send alerts",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return

    if step == "max_trade_amount":
        try:
            amount = float(text)
            if amount <= 0 or amount > 10000:
                await update.message.reply_text("❌ Amount must be between 0 and 10000 USDC")
                return

            telegram_id = update.effective_user.id
            agent_id = agent_db.create_agent(
                telegram_id=telegram_id,
                discord_channel_id=context.user_data["agent_channel_id"],
                agent_name=context.user_data.get("agent_name") or context.user_data.get("agent_channel_name"),
                discord_channel_name=context.user_data.get("agent_channel_name"),
                auto_trade_enabled=bool(context.user_data.get("agent_autotrade")),
                max_trade_amount_usdc=amount,
            )

            await update.message.reply_text(
                f"✅ *AGENT CREATED!*\n\n🆔 Agent ID: `{agent_id}`\n📡 Channel: {context.user_data.get('agent_channel_name')}\n🤖 Auto-trade: {context.user_data.get('agent_autotrade')}\n💰 Max amount: ${amount} USDC\n🟢 Status: ACTIVE",
                parse_mode="Markdown",
            )

            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please send a number.")


async def handle_autotrade_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "agent_autotrade_yes":
        context.user_data["agent_autotrade"] = True
        context.user_data["agent_creation_step"] = "max_trade_amount"

        await query.edit_message_text(
            "*Final Step:* Set maximum trade amount per signal (in USDC):\nRecommended: $10-50 for demo/testing\nExample: Send `20` for $20 USDC max",
            parse_mode="Markdown",
        )
        return

    # NO - alerts only
    context.user_data["agent_autotrade"] = False
    telegram_id = query.from_user.id
    agent_id = agent_db.create_agent(
        telegram_id=telegram_id,
        discord_channel_id=context.user_data.get("agent_channel_id"),
        agent_name=context.user_data.get("agent_name") or context.user_data.get("agent_channel_name"),
        discord_channel_name=context.user_data.get("agent_channel_name"),
        auto_trade_enabled=False,
        max_trade_amount_usdc=0,
    )

    context.user_data.clear()

    await query.edit_message_text(
        f"✅ *AGENT CREATED!*\n\n🆔 Agent ID: `{agent_id}`\n📡 Channel: {context.user_data.get('agent_channel_name', 'Custom')}\n🤖 Mode: ALERTS ONLY\n🟢 Status: ACTIVE",
        parse_mode="Markdown",
    )


async def handle_list_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    telegram_id = query.from_user.id
    agents = agent_db.get_user_agents(telegram_id)

    if not agents:
        await query.edit_message_text(
            "You don't have any agents yet. Create your first agent to get started!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Create Agent", callback_data="agent_create")]]),
        )
        return

    text = "*Your TGE Agents:*\n\n"
    keyboard = []

    for agent in agents:
        status_emoji = "🟢" if agent["status"] == "active" else "⏸"
        trade_emoji = "💸" if agent["auto_trade_enabled"] else "🔔"

        text += f"{status_emoji} *Agent #{agent['id']}*\n📡 {agent.get('discord_channel_name') or 'Custom Channel'}\n{trade_emoji} {('Auto-trade: $' + str(agent['max_trade_amount_usdc'])) if agent['auto_trade_enabled'] else 'Alerts only'}\n\n"

        keyboard.append([InlineKeyboardButton(f"⚙️ Manage Agent #{agent['id']}", callback_data=f"agent_manage_{agent['id']}")])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="agent_menu")])

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# Mapping for callback dispatch
AGENT_HANDLERS = {
    "agent_menu": show_agent_menu,
    "agent_create": handle_create_agent,
    "agent_channel_custom": handle_custom_channel,
    "agent_autotrade_yes": handle_autotrade_choice,
    "agent_autotrade_no": handle_autotrade_choice,
    "agent_list": handle_list_agents,
}

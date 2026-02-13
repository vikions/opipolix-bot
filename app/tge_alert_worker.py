import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from tge_alert_config import find_keywords, format_keywords, truncate_text
from tge_alert_db import TgeAlertDatabase
from tge_discord_monitor import DiscordMonitor
from tge_projects import get_project_config
from agent_db import AgentDatabase
from tge_agent import TGEAgent
from clob_trading import trade_market
from wallet_manager import WalletManager


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class TgeAlertWorker:
    def __init__(self, telegram_token: str, discord_token: Optional[str]):
        self.db = TgeAlertDatabase()
        self.bot = Bot(token=telegram_token)

        self.discord_monitor = None
        if discord_token:
            self.discord_monitor = DiscordMonitor(discord_token, min_interval_sec=60)
        else:
            logger.warning("Discord monitoring disabled")

        self.check_interval = 30
        self._running = True

        logger.info("TGE Alert worker initialized (interval=%ss)", self.check_interval)

    async def send_notification(self, telegram_id: int, message: str) -> None:
        try:
            await self.bot.send_message(chat_id=telegram_id, text=message)
            logger.info("Sent TGE alert to %s", telegram_id)
        except TelegramError:
            logger.exception("Failed to send TGE alert to %s", telegram_id)

    async def check_discord_alerts(self) -> None:
        if not self.discord_monitor:
            logger.debug("Discord monitoring disabled (missing token)")
            return

        alerts = self.db.get_active_alerts()
        if not alerts:
            logger.info("TGE Discord check: no active alerts")
            return

        projects = self._group_alerts_by_project(alerts)
        logger.info("TGE Discord check: %s alerts across %s projects", len(alerts), len(projects))

        for project_name, data in projects.items():
            try:
                channel_id = data.get("discord_channel_id")
                if not channel_id:
                    logger.info("Discord channel not configured for %s", project_name)
                    continue

                logger.info("Discord scan %s (channel %s)", project_name, channel_id)
                messages = await self.discord_monitor.fetch_messages(channel_id, limit=10)
                if not messages:
                    continue

                last_seen = self.db.get_last_discord_message_id(project_name, channel_id)
                if not last_seen:
                    newest = self._max_message_id(messages)
                    if newest:
                        self.db.set_last_discord_message_id(project_name, channel_id, newest)
                    logger.info("Initialized Discord cursor for %s", project_name)
                    continue

                new_messages = self._filter_new_messages(messages, last_seen)
                if not new_messages:
                    continue
                logger.info("New Discord messages for %s: %s", project_name, len(new_messages))

                config = get_project_config(project_name)
                channel_label = self._format_channel_label(channel_id, config)
                server_id = config.discord_server_id if config else None

                for msg in new_messages:
                    content = msg.get("content", "")
                    if not content:
                        continue

                    for alert in data.get("alerts", []):
                        matches = find_keywords(content, alert.get("keywords"))
                        if not matches:
                            continue

                        message = self._build_discord_alert_message(
                            project_name=project_name,
                            channel_label=channel_label,
                            author_name=msg.get("author_name", "unknown"),
                            timestamp=msg.get("timestamp", ""),
                            keywords=matches,
                            content=content,
                            link=self._format_discord_link(server_id, channel_id, msg.get("id")),
                        )
                        await self.send_notification(alert["telegram_id"], message)

                newest = self._max_message_id(messages)
                if newest:
                    self.db.set_last_discord_message_id(project_name, channel_id, newest)
            except Exception:
                logger.exception("Discord check failed for %s", project_name)

    async def run(self) -> None:
        logger.info("TGE Alert worker started")

        while self._running:
            try:
                logger.info("TGE check tick")
                await self.check_discord_alerts()
            except Exception:
                logger.exception("Unexpected error during TGE alert checks")

            await asyncio.sleep(self.check_interval)

        logger.info("TGE Alert worker stopped")

    async def shutdown(self) -> None:
        self._running = False
        if self.discord_monitor:
            await self.discord_monitor.close()

    def _group_alerts_by_project(self, alerts: List[Dict]) -> Dict[str, Dict]:
        projects: Dict[str, Dict] = {}
        for alert in alerts:
            project_name = alert.get("project_name")
            if not project_name:
                continue
            entry = projects.setdefault(
                project_name, {"alerts": [], "discord_channel_id": alert.get("discord_channel_id")}
            )
            if not entry.get("discord_channel_id") and alert.get("discord_channel_id"):
                entry["discord_channel_id"] = alert.get("discord_channel_id")
            entry["alerts"].append(alert)
        return projects

    def _filter_new_messages(self, messages: List[Dict], last_seen: str) -> List[Dict]:
        try:
            last_seen_id = int(last_seen)
        except (TypeError, ValueError):
            last_seen_id = 0

        new_items = []
        for msg in messages:
            try:
                msg_id = int(msg.get("id"))
            except (TypeError, ValueError):
                continue
            if msg_id > last_seen_id:
                new_items.append(msg)

        new_items.sort(key=lambda item: int(item["id"]))
        return new_items

    def _max_message_id(self, messages: List[Dict]) -> Optional[str]:
        ids = []
        for msg in messages:
            try:
                ids.append(int(msg.get("id")))
            except (TypeError, ValueError):
                continue
        if not ids:
            return None
        return str(max(ids))

    def _format_channel_label(self, channel_id: str, config) -> str:
        if config and config.discord_channel_name:
            return f"#{config.discord_channel_name}"
        return f"#{channel_id}"

    def _format_discord_link(
        self, server_id: Optional[str], channel_id: str, message_id: Optional[str]
    ) -> str:
        if not server_id or not message_id:
            return "N/A"
        return f"https://discord.com/channels/{server_id}/{channel_id}/{message_id}"

    def _format_time(self, timestamp: str) -> str:
        if not timestamp:
            return "unknown"
        try:
            cleaned = timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return timestamp

    def _build_discord_alert_message(
        self,
        project_name: str,
        channel_label: str,
        author_name: str,
        timestamp: str,
        keywords: List[str],
        content: str,
        link: str,
    ) -> str:
        return (
            f"🚨 TGE ALERT: {project_name}\n"
            f"📢 New message in {channel_label}\n"
            f"👤 Author: {author_name}\n"
            f"⏰ Time: {self._format_time(timestamp)}\n"
            f"🔑 Keywords found: {format_keywords(keywords)}\n"
            "💬 Message:\n"
            f"{truncate_text(content)}\n"
            f"🔗 Read full: {link}"
        )

"""
Agent-based TGE Alert Worker

This worker runs active user agents, checks their configured Discord channels,
passes messages through the `TGEAgent` pipeline and optionally executes trades.
"""

agent_db = AgentDatabase()
alert_db = TgeAlertDatabase()
discord_monitor = None
agent_core = TGEAgent()
wallets = WalletManager()


async def process_agent(agent: dict):
    agent_id = agent["id"]
    channel_id = agent["discord_channel_id"]
    telegram_id = agent["telegram_id"]
    max_trade_amount = agent.get("max_trade_amount_usdc", 10.0)
    auto_trade_enabled = bool(agent.get("auto_trade_enabled"))

    print(f"\n🤖 Agent #{agent_id}: Checking channel {channel_id}...")

    global discord_monitor
    if not discord_monitor:
        discord_token = os.getenv("DISCORD_TOKEN")
        if discord_token:
            discord_monitor = DiscordMonitor(discord_token, min_interval_sec=30)
        else:
            print("Discord token not configured; skipping agent checks.")
            return

    messages = await discord_monitor.fetch_messages(channel_id, limit=10)
    if not messages:
        return

    last_seen = alert_db.get_last_discord_message_id(f"agent_{agent_id}", channel_id)
    if not last_seen:
        newest = max(int(m.get("id")) for m in messages if m.get("id"))
        alert_db.set_last_discord_message_id(f"agent_{agent_id}", channel_id, str(newest))
        print(f"Initialized cursor for agent #{agent_id}")
        return

    new_msgs = [m for m in messages if int(m.get("id")) > int(last_seen)]
    if not new_msgs:
        return

    print(f"📨 Agent #{agent_id} found {len(new_msgs)} new messages")

    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

    for msg in new_msgs:
        try:
            await process_message_with_agent(agent, msg, bot)
        except Exception as e:
            print(f"Error processing message {msg.get('id')}: {e}")

    latest_id = max(int(m.get("id")) for m in messages if m.get("id"))
    alert_db.set_last_discord_message_id(f"agent_{agent_id}", channel_id, str(latest_id))


async def process_message_with_agent(agent: dict, message: dict, bot: Bot):
    agent_id = agent["id"]
    telegram_id = agent["telegram_id"]
    max_trade_amount = agent.get("max_trade_amount_usdc", 10.0)
    auto_trade_enabled = bool(agent.get("auto_trade_enabled"))

    print(f"\n🧠 Agent #{agent_id} analyzing message: {message.get('content')[:120]}...")

    decision = await agent_core.analyze_signal(
        message_content=message.get("content", ""),
        project_name=agent.get("discord_channel_name") or str(agent.get("discord_channel_id")),
        channel_info={"channel_id": message.get("channel_id"), "author": message.get("author_name")},
        max_trade_amount=max_trade_amount,
    )

    # Log decision
    agent_db.log_decision(
        agent_id=agent_id,
        discord_message_id=message.get("id"),
        signal_text=(message.get("content") or "")[:2000],
        confidence_score=decision.get("confidence", 0.0),
        action=decision.get("action", "monitor"),
        reasoning=decision.get("reasoning", ""),
        market_data=decision.get("market_data"),
        predictos_analysis=decision.get("predictos_analysis"),
        discovered_tools=decision.get("discovered_tools"),
    )

    # Build notification
    notification = build_agent_notification(message, decision, agent)

    await bot.send_message(chat_id=telegram_id, text=notification, parse_mode="Markdown")

    # If trade recommended and allowed, execute
    if decision.get("action") == "trade" and auto_trade_enabled:
        await execute_agent_trade(agent, decision, bot, telegram_id)


def build_agent_notification(message: dict, decision: dict, agent: dict) -> str:
    action = decision.get("action", "monitor")
    emoji = {"trade": "💸", "monitor": "👀", "ignore": "🚫"}.get(action, "❓")
    conf = decision.get("confidence", 0.0)
    conf_pct = f"{conf:.1%}"
    keywords = ", ".join(decision.get("keywords_found", [])[:5])

    text = f"🤖 *AGENT #{agent['id']} ANALYSIS*\n\n"
    text += f"📢 Author: {message.get('author_name')}\n"
    text += f"💬 {message.get('content')[:300]}{'...' if len(message.get('content',''))>300 else ''}\n\n"
    text += f"{emoji} *Action:* {action.upper()}\n"
    text += f"📊 *Confidence:* {conf_pct}\n"
    text += f"🔑 *Keywords:* {keywords}\n\n"
    text += f"*Reasoning:*\n{decision.get('reasoning','')}\n\n"

    if decision.get("predictos_analysis"):
        pa = decision["predictos_analysis"]
        text += f"*PredictOS:* intent={pa.get('intent')} confidence={pa.get('confidence'):.2f}\n"

    if decision.get("discovered_tools"):
        text += f"*x402 tools discovered:* {len(decision.get('discovered_tools',[]))}\n"

    if decision.get("market_data"):
        bm = decision["market_data"].get("best_market")
        if bm:
            text += f"\n*Market:* {bm.get('question')}\nLiquidity: ${bm.get('liquidity',0):,.0f}\nYES price: {bm.get('current_yes_price',0):.2f}\nOpportunity: {bm.get('opportunity_score',0):.2f}\n"

    if decision.get("action") == "trade" and decision.get("trade_params"):
        tp = decision["trade_params"]
        text += f"\n*TRADE:* ${tp.get('amount_usdc')} {tp.get('side')} @ ~{tp.get('expected_price')}\n"

    return text


async def execute_agent_trade(agent: dict, decision: dict, bot: Bot, telegram_id: int):
    tp = decision.get("trade_params") or {}
    clob_token = tp.get("clob_token_yes")
    amount = tp.get("amount_usdc")

    if not clob_token or not amount:
        await bot.send_message(chat_id=telegram_id, text="❌ Trade params incomplete; cannot execute.")
        return

    # Get user's wallet
    wallet = wallets.get_wallet(telegram_id)
    if not wallet:
        await bot.send_message(chat_id=telegram_id, text="❌ No wallet found for this user; cannot execute trade.")
        return

    private_key = wallets.get_private_key(telegram_id)

    try:
        result = trade_market(
            user_private_key=private_key,
            token_id=clob_token,
            side="BUY",
            amount_usdc=amount,
            telegram_id=telegram_id,
            funder_address=wallet.get("safe_address"),
        )
    except Exception as e:
        await bot.send_message(chat_id=telegram_id, text=f"❌ Trade failed: {e}")
        return

    order_id = result.get("order_id")

    # Update log entry with trade result -- append via new log (simple)
    agent_db.log_decision(
        agent_id=agent["id"],
        discord_message_id=decision.get("discord_message_id"),
        signal_text=(decision.get("predictos_analysis",{}).get("raw_text") or "")[:2000],
        confidence_score=decision.get("confidence",0.0),
        action="trade_executed",
        reasoning=decision.get("reasoning",""),
        trade_executed=True,
        trade_amount_usdc=amount,
        trade_order_id=str(order_id),
    )

    await bot.send_message(
        chat_id=telegram_id,
        text=f"✅ *TRADE EXECUTED*\n\nOrder ID: `{order_id}`\nAmount: ${amount}\n",
        parse_mode="Markdown",
    )


async def check_agents_once():
    active = agent_db.get_active_agents()
    if not active:
        print("No active agents")
        return
    print(f"Monitoring {len(active)} agents...")
    for a in active:
        try:
            await process_agent(a)
        except Exception as e:
            print(f"Error processing agent {a.get('id')}: {e}")


async def run_worker():
    print("🚀 TGE Agent Worker started")
    while True:
        try:
            await check_agents_once()
        except Exception as e:
            print(f"Worker error: {e}")
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run_worker())

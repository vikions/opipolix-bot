import asyncio
import os
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

from database import Database
from opinion_price_monitor import OpinionPriceMonitor
from opinion_tracked_markets import CHILD_TO_PROJECT
from worker_health import get_monitor


class OpinionAlertWorker:
    def __init__(self, telegram_token: str):
        self.db = Database()
        self.price_monitor = OpinionPriceMonitor()
        self.bot = Bot(token=telegram_token)
        self.health_monitor = get_monitor()

        self.check_interval = 30

        print("[Opinion] Alert worker initialized.")

    async def send_notification(self, telegram_id: int, message: str):
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            print(f"[Opinion] Alert notification sent to {telegram_id}")
        except TelegramError as e:
            print(f"[Opinion] Failed to send notification to {telegram_id}: {e}")

    async def check_and_trigger_alerts(self):
        active_alerts = self.db.get_active_opinion_alerts()

        if not active_alerts:
            return

        print(f"[Opinion] Checking {len(active_alerts)} active alerts...")

        for alert in active_alerts:
            try:
                market_id = alert["market_id"]
                alert_type = alert["alert_type"]
                trigger_percent = alert["trigger_percent"]

                triggered = await self.price_monitor.check_trigger(
                    market_id=market_id,
                    alert_type=alert_type,
                    trigger_percent=trigger_percent
                )

                if triggered:
                    self.db.update_opinion_alert_status(alert["id"], "triggered")
                    self.health_monitor.mark_order_executed()

                    project = CHILD_TO_PROJECT.get(market_id, f"Market {market_id}")
                    type_label = "Pump" if alert_type == "price_pump" else "Dump"

                    message = (
                        "*Opinion Alert Triggered*\n\n"
                        f"{project} (#{market_id})\n"
                        f"Type: {type_label}\n"
                        f"Trigger: {trigger_percent}%\n"
                        f"Alert ID: `{alert['id']}`"
                    )

                    await self.send_notification(alert["telegram_id"], message)

                    self.price_monitor.reset_initial_price(market_id)

            except Exception as e:
                print(f"[Opinion] Error processing alert #{alert.get('id')}: {e}")
                self.health_monitor.mark_error(str(e))
                import traceback
                traceback.print_exc()

    async def run(self):
        print("[Opinion] Alert worker started.")
        print(f"[Opinion] Check interval: {self.check_interval} seconds")

        self.health_monitor.mark_started()

        iteration = 0

        while True:
            try:
                iteration += 1
                timestamp = datetime.now().strftime("%H:%M:%S")

                print(f"[{timestamp}] Iteration #{iteration}")

                active_alerts = self.db.get_active_opinion_alerts()
                active_count = len(active_alerts) if active_alerts else 0

                await self.check_and_trigger_alerts()

                self.health_monitor.mark_iteration(active_count)

                await asyncio.sleep(self.check_interval)

            except KeyboardInterrupt:
                print("\n[Opinion] Alert worker stopped by user")
                self.health_monitor.mark_stopped()
                break
            except Exception as e:
                print(f"[Opinion] Error in main loop: {e}")
                self.health_monitor.mark_error(str(e))
                import traceback
                traceback.print_exc()

                await asyncio.sleep(self.check_interval)


async def main():
    telegram_token = os.getenv("TELEGRAM_TOKEN")

    if not telegram_token:
        print("[Opinion] TELEGRAM_TOKEN not found in environment.")
        return

    worker = OpinionAlertWorker(telegram_token)
    await worker.run()


if __name__ == "__main__":
    print("=" * 60)
    print("OpiPoliX Opinion Alert Worker")
    print("=" * 60)

    asyncio.run(main())

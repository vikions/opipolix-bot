# OpiPoliX Bot

Telegram bot that tracks spreads on hype token launch prediction markets
across **Opinion** and **Polymarket** (e.g. MetaMask and Base token launch).

## Quick start

```bash
git clone https://github.com/vikions/opipolix-bot.git
cd opipolix-bot
python -m venv .venv
# activate venv
pip install -r requirements.txt
cp .env.example .env  # fill in keys
python app/bot.py

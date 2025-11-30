# 🚀 OpiPoliX Bot

<img src="logo.png" alt="OpiPoliX Logo" width="120"/>

### 📲 Live Telegram Bot  
👉 **https://t.me/OpiPoliXBot**

OpiPoliX is a real-time Telegram bot that tracks *pricing spreads* for high-impact crypto prediction markets across **Opinion.trade (CLOB)** and **Polymarket**.

Designed for traders, researchers, and degens who want signal without noise.

---

## 🔍 What OpiPoliX Does

| Feature | Status |
|--------|--------|
| 🔎 Fetch market data from Opinion | ✔️ Live |
| 🔎 Fetch market data from Polymarket | ✔️ Live |
| 📊 Calculate real-time spreads | ✔️ Live |
| 📲 One-click query via Telegram | ✔️ Live |
| 💸 API attribution for trading | 🔜 Coming next |
| 📈 Expand to more launch prediction markets | 🔜 In progress |

Currently tracking:
- **MetaMask token launch (2025)**
- **Base token launch (2025)**
- More high-hype crypto markets coming soon…

---

## 🧠 Why

Most traders track token launch rumors via Twitter, Discord, or CT noise.  
**OpiPoliX reads direct market data instead**, helping you see what real money thinks.

---

## 🚀 Quick Start (Local Dev)

```bash
git clone https://github.com/vikions/opipolix-bot.git
cd opipolix-bot

python -m venv .venv
# Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

cp .env.example .env  # Fill in all keys (Telegram, Opinion, Polymarket)

python app/bot.py
🔑 Required Environment Variables
Create a .env file and set:

env
Copy code
TELEGRAM_TOKEN=your_telegram_bot_token
API_KEY=your_opinion_api_key
RPC_URL=https://bsc-dataseed.binance.org
PRIVATE_KEY=your_private_key
MULTI_SIG_ADDRESS=your_multisig_wallet
HOST=https://proxy.opinion.trade:8443
CHAIN_ID=56

POLYMARKET_API_KEY=your_polymarket_api_key
📦 Deploy to Production
We currently run this project using Railway.app (recommended for bots).

Main requirements:

Python 3.11+

requirements.txt auto-installed

Railway automatically runs:

bash
Copy code
python app/bot.py
🌐 Roadmap
🛒 Enable real trading via APIs (with market attribution)

📊 Add aggregated market dashboard

📱 Add trading signals (e.g. “Spread > 10%” alerts)

📢 Twitter & Discord auto announcements

🧠 Expand to more token launch markets

🧩 Tech Stack
Python + python-telegram-bot

Opinion CLOB SDK

Polymarket Gamma API

Railway cloud deployment

👤 Author
Built by @vikions — Crypto dev & prediction markets researcher.

Twitter: <soon...>
Telegram Bot: https://t.me/OpiPoliXBot

🤝 Contributions
Contributions, market suggestions, and spread ideas are welcome!
Feel free to open PRs/issues or DM via Telegram.

⚠ Disclaimer
OpiPoliX Bot is a market data analysis tool.
It does not provide financial advice. Trading involves risk.

💬 “Don’t scroll Twitter for rumors. Read what the market actually prices in.”
— OpiPoliX

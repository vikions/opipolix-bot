# 🤖 OpiPoliX Bot

**Smart Telegram Trading Bot for Polymarket Prediction Markets**

[![Live Bot](https://img.shields.io/badge/Telegram-@OpiPoliXBot-blue?logo=telegram)](https://t.me/OpiPoliXBot)
[![Python](https://img.shields.io/badge/Python-3.11+-green?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 What is OpiPoliX?

OpiPoliX is a **full-featured Telegram trading bot** for Polymarket prediction markets. Trade crypto token launch markets directly from Telegram with:

- ⚡ **Gasless trading** - No transaction fees
- 🔐 **Smart Account wallets** - Secure Safe{Core} integration  
- 🤖 **Auto-Trade triggers** - Set price alerts and auto-execute
- 📊 **Real-time spreads** - Compare Opinion vs Polymarket pricing
- 💰 **Easy withdrawals** - One command to move funds

**Live Bot:** [@OpiPoliXBot](https://t.me/OpiPoliXBot)

---

## ✨ Features

### 🔐 Wallet Management
- **Automatic wallet creation** - EOA + Safe wallet deployed on first use
- **Gasless deployment** - Polymarket covers all gas fees
- **Secure key storage** - Encrypted private keys in PostgreSQL
- **Balance checking** - Real-time USDC and position balances

### 📈 Manual Trading
- **Buy/Sell YES or NO** tokens
- **Percentage-based selling** - Sell 25%, 50%, 75%, or 100% of holdings
- **Market execution** - Instant fills at best available prices
- **Transaction history** - Track all your trades

### 🤖 Auto-Trade (Unique Feature!)
Set automated triggers and let the bot trade for you:

**Three strategies available:**

1. **📈 Buy YES on Pump** - Real news strategy
   - Automatically buy YES when price pumps
   - Example: "Buy $10 YES if price rises +15%"
   - Perfect for: Catching real token launches

2. **🎭 Buy NO on Pump** - Fake news strategy  
   - Automatically buy NO when YES pumps hard
   - Example: "Buy $20 NO if YES pumps +50%"
   - Perfect for: Fading fake news pumps

3. **📉 Buy NO on Dump** - Safety net strategy
   - Automatically buy NO when YES dumps
   - Example: "Buy $5 NO if YES drops -30%"  
   - Perfect for: Confirming fake news after dump

**How it works:**
- Background worker monitors prices every 10 seconds
- Triggers execute automatically when conditions met
- Retry logic with decreasing amounts (3 attempts)
- Real-time notifications on trigger and execution
- All trades are gasless!

### 📊 Market Analysis
- **Real-time spreads** - Compare Opinion vs Polymarket prices
- **Market info** - See current YES/NO pricing
- **Active orders** - View and manage your auto-trade triggers

### Telegram Widget (Pinned Board)
- **Pinned board message** in your group/channel (no spam)
- **Select 1-5 markets** and auto-update YES/NO values
- **Needs only Pin messages + Edit messages** permissions

### 💸 Withdrawals
- **Easy USDC withdrawal** - One command to any address
- **Gasless transactions** - No fees for withdrawals
- **Safe and secure** - Transactions signed by your wallet

---

## 🚀 Quick Start

### For Users

1. **Open Telegram** → Search for [@OpiPoliXBot](https://t.me/OpiPoliXBot)
2. **Press /start** → Bot creates your wallet automatically
3. **Deposit USDC** → Send to your Safe address (Polygon network)
4. **Start trading!** → Use Markets menu

### For Developers

```bash
# Clone repository
git clone https://github.com/vikions/opipolix-bot.git
cd opipolix-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your credentials

# Run bot
python app/bot.py

# Run auto-trade worker (in separate terminal)
python app/auto_trade_worker.py

# Run widget worker (in separate terminal)
python app/widget_worker.py
```

---

## 🔧 Configuration

### Required Environment Variables

```env
# Telegram
TELEGRAM_TOKEN=your_telegram_bot_token

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Encryption
MASTER_KEY=your_32_byte_encryption_key

# Polymarket CLOB API
BUILDER_API_KEY=your_clob_api_key
BUILDER_API_SECRET=your_clob_api_secret  
BUILDER_API_PASSPHRASE=your_clob_passphrase
BUILDER_SIGNING_URL=your_signing_service_url

# Blockchain
POLY_RPC_URL=https://polygon-rpc.com
RELAYER_URL=https://relayer.polymarket.com

# Opinion API (for spread checking)
OPINION_API_KEY=your_opinion_api_key
OPINION_API_SECRET=your_opinion_api_secret
```

---

## 📁 Project Structure

```
opipolix-bot/
├── app/
│   ├── bot.py                    # Main Telegram bot
│   ├── auto_trade_worker.py      # Background price monitor
│   ├── auto_trade_handlers.py    # Auto-trade UI handlers
│   ├── auto_trade_manager.py     # Order management
│   ├── price_monitor.py          # Price tracking logic
│   ├── clob_trading.py           # Trading execution
│   ├── wallet_manager.py         # Wallet creation & Safe deployment
│   ├── database.py               # PostgreSQL interface
│   ├── market_config.py          # Market definitions
│   └── ...
├── start.py                      # Production runner (bot + worker)
├── requirements.txt              # Python dependencies
├── Procfile                      # Railway deployment config
└── README.md                     # This file
```

---

## 🎮 Usage Examples

### Manual Trading
```
1. Open bot → Trading → Markets → MetaMask Token
2. Press "📈 Buy YES"  
3. Enter amount: 10
4. ✅ Transaction confirmed (gasless!)
```

### Telegram Widget (Pinned Board)
```
1. Open bot → 📌 Telegram Widget → Create widget
2. Add @OpiPolixBot to your group/channel as admin
3. Grant ONLY: Pin messages + Edit messages
4. Select chat, markets, and update interval
5. ✅ Widget is posted and pinned
```

### Auto-Trade Setup
```
1. Open bot → Markets → MetaMask Token → Auto-Trade
2. Press "📈 Buy YES on Pump"
3. Enter trigger: 15 (for +15% price change)
4. Enter amount: 20  
5. ✅ Order created! Bot now monitors 24/7
```

### Check Balances
```
1. Open bot → Trading → Check Balance
2. See: USDC balance + YES/NO positions
```

### Withdraw Funds
```
1. Open bot → Trading → Withdraw
2. Send: /withdraw 50 0x742d...5aB2
3. ✅ 50 USDC sent to your address (gasless!)
```

---

## 🏗️ Architecture

### Two-Process System

**Bot Process** (`bot.py`)
- Handles Telegram UI
- Processes user commands
- Creates/cancels orders
- Displays balances

**Worker Process** (`auto_trade_worker.py`)  
- Monitors prices every 10 seconds
- Checks active order triggers
- Executes trades automatically
- Sends notifications

**Widget Worker** (`widget_worker.py`)
- Updates pinned widget boards on schedule
- Edits existing widget messages (no spam)
- Skips edits when values do not change

### Key Technologies

- **Telegram Bot API** - User interface
- **py-clob-client** - Polymarket CLOB integration
- **Safe{Core}** - Smart account wallets
- **PostgreSQL** - Order & wallet storage
- **Web3.py** - Blockchain interactions
- **Polymarket Relayer** - Gasless transactions

---

## 🎯 Supported Markets

Currently tracking high-hype crypto token launch markets:

- 🦊 **MetaMask Token 2025** - Will MetaMask launch a token?
- 🔵 **Base Token 2025** - Will Base launch a token?

More markets added regularly based on community interest!

---

## 🚢 Deployment

### Railway (Recommended)

1. **Fork this repo**
2. **Connect to Railway**
3. **Add environment variables**
4. **Deploy!**

Railway will automatically:
- Run `start.py` (launches both bot + worker)
- Connect to PostgreSQL
- Handle scaling

### Manual Deployment

Run three processes:

```bash
# Terminal 1 - Bot
python app/bot.py

# Terminal 2 - Auto-trade Worker
python app/auto_trade_worker.py

# Terminal 3 - Widget Worker
python app/widget_worker.py
```

Or use the combined launcher:

```bash
python start.py
```

---

## 🛣️ Roadmap

- [x] Manual trading (Buy/Sell)
- [x] Auto-Trade with triggers  
- [x] Gasless Safe wallet deployment
- [x] Percentage-based selling
- [x] Real-time balance checking
- [ ] Add more token launch markets
- [ ] Trading history & analytics
- [ ] Multi-market auto-orders
- [ ] Advanced charting
- [ ] Mobile notifications
- [ ] Web dashboard

---

## 🤝 Contributing

Contributions welcome! Feel free to:

- 🐛 Report bugs
- 💡 Suggest features  
- 🔧 Submit pull requests
- 📝 Improve documentation

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file

---

## ⚠️ Disclaimer

**OpiPoliX is a trading tool, not financial advice.**

- Trading prediction markets involves risk
- Only trade with funds you can afford to lose
- Do your own research (DYOR)
- Bot is provided "as-is" without warranties

---

## 👤 Author

Built by **@vikions**

- Crypto developer & prediction markets enthusiast
- Telegram: [@OpiPoliXBot](https://t.me/OpiPoliXBot)
- Twitter: https://x.com/opipolixbot

---

## 💬 Support

**Having issues?**

1. Check the [FAQ](#) 
2. Open an [issue](https://github.com/vikions/opipolix-bot/issues)  


---

**⚡ "Trade smarter, not harder. Automate your Polymarket strategy."** - OpiPoliX

---

**Star ⭐ this repo if you find it useful!**

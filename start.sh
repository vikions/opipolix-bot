#!/bin/bash

echo "🚀 Starting OpiPoliX Bot with auto-restart..."

# Function to run bot with restart
run_bot() {
    while true; do
        echo "▶️  Starting bot..."
        python app/bot.py
        EXIT_CODE=$?
        
        echo "❌ Bot crashed with exit code $EXIT_CODE"
        echo "⏳ Waiting 5 seconds before restart..."
        sleep 5
        echo "🔄 Restarting bot..."
    done
}

# Function to run worker with restart
run_worker() {
    while true; do
        echo "▶️  Starting worker..."
        python app/auto_trade_worker.py
        EXIT_CODE=$?
        
        echo "❌ Worker crashed with exit code $EXIT_CODE"
        echo "⏳ Waiting 5 seconds before restart..."
        sleep 5
        echo "🔄 Restarting worker..."
    done
}

# Run both in background with auto-restart
run_bot &
run_worker &

# Wait forever (both processes restart automatically)
wait

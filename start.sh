#!/bin/bash

echo "Starting OpiPoliX Bot with auto-restart..."

# Function to run bot with restart
run_bot() {
    while true; do
        echo "Starting bot..."
        python app/bot.py
        EXIT_CODE=$?

        echo "Bot crashed with exit code $EXIT_CODE"
        echo "Waiting 5 seconds before restart..."
        sleep 5
        echo "Restarting bot..."
    done
}

# Function to run auto-trade worker with restart
run_auto_trade_worker() {
    while true; do
        echo "Starting auto-trade worker..."
        python app/auto_trade_worker.py
        EXIT_CODE=$?

        echo "Auto-trade worker crashed with exit code $EXIT_CODE"
        echo "Waiting 5 seconds before restart..."
        sleep 5
        echo "Restarting auto-trade worker..."
    done
}

# Function to run opinion alert worker with restart
run_opinion_alert_worker() {
    while true; do
        echo "Starting opinion alert worker..."
        python app/opinion_alert_worker.py
        EXIT_CODE=$?

        echo "Opinion alert worker crashed with exit code $EXIT_CODE"
        echo "Waiting 5 seconds before restart..."
        sleep 5
        echo "Restarting opinion alert worker..."
    done
}

# Function to run TGE alert worker with restart
run_tge_alert_worker() {
    while true; do
        echo "Starting TGE alert worker..."
        python app/tge_alert_worker.py
        EXIT_CODE=$?

        echo "TGE alert worker crashed with exit code $EXIT_CODE"
        echo "Waiting 5 seconds before restart..."
        sleep 5
        echo "Restarting TGE alert worker..."
    done
}

# Function to run widget worker with restart
run_widget_worker() {
    while true; do
        echo "Starting widget worker..."
        python app/widget_worker.py
        EXIT_CODE=$?

        echo "Widget worker crashed with exit code $EXIT_CODE"
        echo "Waiting 5 seconds before restart..."
        sleep 5
        echo "Restarting widget worker..."
    done
}

# Run all workers in background with auto-restart
run_bot &
run_auto_trade_worker &
run_opinion_alert_worker &
run_tge_alert_worker &
run_widget_worker &

# Wait forever (all processes restart automatically)
wait

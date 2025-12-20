#!/bin/bash

# Start both bot and worker
python app/bot.py &
python app/auto_trade_worker.py &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?

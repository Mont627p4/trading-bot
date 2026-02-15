#!/bin/bash
echo "=================================="
echo "Starting Telegram Trading Bot"
echo "=================================="

# Start the Python bot in background
echo "🚀 Starting bot process..."
python trading_bot.py &

# Start the web server
echo "🌐 Starting web server..."
gunicorn app:app

# Keep the script running
wait

from flask import Flask
import logging
import subprocess
import sys
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Bot is running with auto-close!"

@app.route('/health')
def health():
    return "OK", 200

# THIS IS THE KEY - Run trading_bot.py as a SEPARATE PROCESS
def start_bot():
    """Start the trading bot as a separate process"""
    try:
        # Run trading_bot.py, NOT as Flask app
        process = subprocess.Popen(
            [sys.executable, 'trading_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        logging.info(f"🚀 Trading bot started with PID: {process.pid}")
        
        # Log output in real-time
        for line in process.stdout:
            logging.info(f"BOT: {line.strip()}")
            
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

# Start bot in background thread
import threading
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()
logging.info("✅ Bot thread initiated")

# This is the Flask server - runs on port 10000
if __name__ == "__main__":
    # Only run Flask, NOT the trading bot
    app.run(host='0.0.0.0', port=10000)

from flask import Flask
import logging
import threading
import subprocess
import sys

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Bot is running with auto-close functionality!"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    """Start trading_bot.py as subprocess"""
    try:
        process = subprocess.Popen([sys.executable, 'trading_bot.py'],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        logging.info(f"🚀 Bot started with PID: {process.pid}")
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

# Start bot in background
thread = threading.Thread(target=run_bot, daemon=True)
thread.start()
logging.info("✅ Bot thread initiated")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

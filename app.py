from flask import Flask
import logging
import subprocess
import sys
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    process = subprocess.Popen(
        [sys.executable, 'trading_bot.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    logging.info(f"🚀 Bot started with PID: {process.pid}")
    
    for line in process.stdout:
        logging.info(f"BOT: {line.strip()}")

thread = threading.Thread(target=run_bot, daemon=True)
thread.start()
logging.info("✅ Bot thread started")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

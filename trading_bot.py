from flask import Flask
import logging
import subprocess
import sys

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Bot is running with auto-close!"

@app.route('/health')
def health():
    return "OK", 200

# Start bot
process = subprocess.Popen([sys.executable, 'trading_bot.py'])
logging.info(f"🚀 Bot started with PID: {process.pid}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

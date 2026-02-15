from flask import Flask
import logging
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

# Start bot as subprocess
try:
    process = subprocess.Popen(
        [sys.executable, 'trading_bot.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    logging.info(f"🚀 Bot started with PID: {process.pid}")
except Exception as e:
    logging.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

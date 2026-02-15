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
    """Start trading_bot.py as subprocess and log its output."""
    try:
        # Start the process and capture stdout and stderr
        process = subprocess.Popen(
            [sys.executable, 'trading_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stdout and stderr
            universal_newlines=True,    # Decode output as text
            bufsize=1                    # Line buffered
        )

        logging.info(f"🚀 Bot started with PID: {process.pid}")

        # Continuously read and log the bot's output line by line
        for line in iter(process.stdout.readline, ''):
            if line:
                # Log each line from the bot script
                logging.info(f"BOT: {line.strip()}")

        # Wait for the process to finish and get the return code
        return_code = process.wait()
        logging.error(f"❌ Bot process exited with code {return_code}")

    except Exception as e:
        logging.error(f"Failed to start or run bot: {e}")

# Start bot in background
thread = threading.Thread(target=run_bot, daemon=True)
thread.start()
logging.info("✅ Bot thread initiated")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

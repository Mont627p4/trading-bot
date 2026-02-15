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

def start_bot():
    """Starts the bot and streams its logs."""
    try:
        # Start the bot process, capturing its output
        process = subprocess.Popen(
            [sys.executable, 'trading_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stdout and stderr
            universal_newlines=True,
            bufsize=1
        )
        logging.info(f"🚀 Bot started with PID: {process.pid}")

        # Continuously read and log the bot's output line by line
        for line in iter(process.stdout.readline, ''):
            if line:
                # This will print the bot's logs directly to your Render logs
                print(f"BOT: {line.strip()}")

        # Wait for the process to finish and log its exit code
        return_code = process.wait()
        logging.error(f"❌ Bot process exited with code {return_code}")

    except Exception as e:
        logging.error(f"Failed to start or run bot: {e}")

# Start the bot in a background thread
import threading
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()
logging.info("✅ Bot thread initiated")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

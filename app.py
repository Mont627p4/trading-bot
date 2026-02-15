from flask import Flask
import logging
import subprocess
import sys
import threading

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Bot is initializing... Check logs for status."

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    """Run the bot and stream all output to logs."""
    try:
        # Start the bot process
        process = subprocess.Popen(
            [sys.executable, 'trading_bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        logging.info(f"🚀 Bot process started with PID: {process.pid}")

        # Read and log output line by line in REAL TIME
        for line in iter(process.stdout.readline, ''):
            if line:
                # CRITICAL: This prints the bot's errors directly to your logs
                print(f"BOT DEBUG: {line.strip()}")
                logging.info(f"BOT: {line.strip()}")

        # Wait for process to finish and log exit code
        return_code = process.wait()
        logging.error(f"❌❌❌ BOT PROCESS EXITED WITH CODE {return_code} ❌❌❌")

    except Exception as e:
        logging.error(f"CRITICAL ERROR in run_bot: {e}")

# Start the bot in a background thread
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
logging.info("✅ Bot thread initiated - waiting for output...")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

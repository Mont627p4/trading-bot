from trading_bot import main
import asyncio
from flask import Flask
import threading
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Bot is running 24/7 on Render!"

def run_bot():
    """Run the bot in a new event loop"""
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run the bot
    loop.run_until_complete(main())

if __name__ == "__main__":
    # Start bot in background thread
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    
    # Run web server
    app.run(host='0.0.0.0', port=10000)
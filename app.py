from flask import Flask
import logging

# Create the Flask application instance. Gunicorn looks for 'app'.
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return "Bot is running in a separate process!"

@app.route('/health')
def health():
    return "OK", 200

# No bot code or thread starting here!
# The bot is started separately by the start.sh script.

# This block is only used if you run 'python app.py' locally for testing.
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

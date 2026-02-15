from telethon import TelegramClient, events
from telethon.sessions import StringSession
from binance.client import Client
import re
import math
import asyncio
import logging
import os

# ========== YOUR CREDENTIALS ==========
API_ID = 38099889  # <-- REPLACE with your REAL API_ID (from my.telegram.org)
API_HASH = "333fe09debc36b6aac46aa60dac30e30"  # <-- REPLACE with your REAL API_HASH
BINANCE_KEY = "ApgzC2cpewhBKqb1YPODfRCPzzV1Cy1y3wtpUiDAk8Dq21o6dFG4r6fcVpISey9W"  # <-- REPLACE with your Binance Testnet Key
BINANCE_SECRET = "TllMkU490TyHO5HORsIF9QZsbgveitB2nb95CWgh39HbmOHz0GSJZnf9mlNa5r95"  # <-- REPLACE with your Binance Testnet Secret
CHANNEL_ID = -1002840783921  # YOUR CHANNEL ID (keep as is)
SESSION_STRING = "1BVtsOLsBu7-3Uaw0j6l5j0saUw58qhJ1cidZFrnw3lEI6nFRILffsW2gDtBX__8WaQZ0zkDRl3HtLs5DY9x-sbiHkJcoX1lXGcG7YDgTfXvqweasefhPC6Vp_F7itL6-LOd9pSueRJCxaNgA-VTNcA2PjfYBxejy7ueKpGD1b-ttjUIXEHX3J1gGPJKS47jMmNdcVN_b2x3JtcFO-nO35gRb1YMaDFfdJ_svj6bbP_hRZo3JLMs6ka31J9MGUMrJjKdQpmoMWMLKfnAeo3OP_kVs-lCFGTB8t7QQhMDqoeuxtDiXy6vBBmN_djpbTl7OSny2OoXbRGeG1Auxa_1fIn-_8a4gV-w="  # <-- REPLACE with your session string
# ======================================

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Risk setting - 1% per trade
RISK_PERCENT = 1

# Initialize Telegram client with session string
telegram_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Initialize Binance client (TESTNET)
binance_client = Client(BINANCE_KEY, BINANCE_SECRET, testnet=True)
binance_client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'

def get_usdt_balance():
    """Get USDT balance from futures account"""
    try:
        balance = binance_client.futures_account_balance()
        for item in balance:
            if item['asset'] == 'USDT':
                logger.info(f"💰 Balance: {item['balance']} USDT")
                return float(item['balance'])
        return 0
    except Exception as e:
        logger.error(f"Balance error: {e}")
        return 0

def calculate_quantity(entry_price, stop_loss, symbol):
    """Calculate position size based on 1% risk"""
    try:
        balance = get_usdt_balance()
        risk_amount = balance * (RISK_PERCENT / 100)
        logger.info(f"📊 Risk amount: {risk_amount} USDT")
        
        # Get symbol info for quantity precision
        info = binance_client.futures_exchange_info()
        step_size = 0.001
        
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for filt in s['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        step_size = float(filt['stepSize'])
                        logger.info(f"📏 Step size for {symbol}: {step_size}")
                        break
        
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            logger.error("❌ Price difference is zero")
            return 0
            
        raw_quantity = risk_amount / price_diff
        logger.info(f"🧮 Raw quantity: {raw_quantity}")
        
        # Round down to step size
        precision = int(round(-math.log10(step_size)))
        quantity = math.floor(raw_quantity * (10 ** precision)) / (10 ** precision)
        
        logger.info(f"✅ Final quantity: {quantity}")
        return quantity
    except Exception as e:
        logger.error(f"Quantity calculation error: {e}")
        return 0

@telegram_client.on(events.NewMessage)
async def handle_signal(event):
    """Process signals from channel"""
    try:
        # Only process messages from your channel
        if event.chat_id != CHANNEL_ID:
            return
            
        text = event.message.text
        logger.info(f"📨 New message from private channel")
        
        # Check if it's a signal
        if not text or 'USDT' not in text:
            return
        if 'LONG' not in text and 'SHORT' not in text:
            return
        
        logger.info(f"🎯 SIGNAL DETECTED!")
        logger.info(f"Signal: {text}")
        
        # Extract data - MODIFY THESE FOR YOUR SIGNAL FORMAT
        pair_match = re.search(r'([A-Z]+USDT)', text)
        entry_match = re.search(r'Entry.*?(\d+\.?\d*)', text, re.IGNORECASE)
        sl_match = re.search(r'SL.*?(\d+\.?\d*)', text, re.IGNORECASE)
        tp1_match = re.search(r'TP1.*?(\d+\.?\d*)', text, re.IGNORECASE)
        lev_match = re.search(r'\((\d+)X\)', text)
        
        if not all([pair_match, entry_match, sl_match, tp1_match]):
            logger.warning("⚠️ Could not extract all signal parameters")
            logger.warning(f"Pair: {pair_match.group(1) if pair_match else 'Not found'}")
            logger.warning(f"Entry: {entry_match.group(1) if entry_match else 'Not found'}")
            logger.warning(f"SL: {sl_match.group(1) if sl_match else 'Not found'}")
            logger.warning(f"TP1: {tp1_match.group(1) if tp1_match else 'Not found'}")
            return
        
        symbol = pair_match.group(1)
        entry_price = float(entry_match.group(1))
        stop_loss = float(sl_match.group(1))
        take_profit = float(tp1_match.group(1))
        
        # Determine side
        side = 'BUY' if 'LONG' in text else 'SELL'
        logger.info(f"📈 Side: {side}")
        
        # Calculate quantity
        quantity = calculate_quantity(entry_price, stop_loss, symbol)
        
        if quantity <= 0:
            logger.error("❌ Invalid quantity calculated")
            return
        
        # Set leverage
        leverage = int(lev_match.group(1)) if lev_match else 5
        logger.info(f"⚡ Leverage: {leverage}X")
        binance_client.futures_change_leverage(symbol=symbol, leverage=leverage)
        
        # Place limit order
        logger.info(f"🔄 Placing LIMIT order: {symbol} {side} {quantity} @ {entry_price}")
        order = binance_client.futures_create_order(
            symbol=symbol,
            side=side,
            type='LIMIT',
            price=entry_price,
            quantity=quantity,
            timeInForce='GTC'
        )
        
        logger.info(f"✅✅✅ ORDER PLACED SUCCESSFULLY!")
        logger.info(f"Order ID: {order['orderId']}")
        
    except Exception as e:
        logger.error(f"❌ Error processing signal: {e}")

async def find_channel():
    """Find the private channel by searching dialogs"""
    logger.info("🔍 Searching for your private channel in dialogs...")
    
    try:
        # Get all dialogs (chats, groups, channels)
        async for dialog in telegram_client.iter_dialogs():
            logger.info(f"Checking: {dialog.name} (ID: {dialog.id})")
            
            # Check if this dialog's ID matches our channel ID
            if dialog.id == CHANNEL_ID:
                logger.info(f"✅✅✅ FOUND YOUR CHANNEL: {dialog.name}")
                logger.info(f"Channel entity: {dialog.entity}")
                return dialog.entity
        
        # If we get here, channel wasn't found
        logger.error(f"❌ Channel with ID {CHANNEL_ID} not found in your dialogs!")
        logger.error("Please make sure:")
        logger.error("1. The CHANNEL_ID is correct (currently: {})".format(CHANNEL_ID))
        logger.error("2. You are a member of this channel")
        logger.error("3. The channel appears in your Telegram chat list")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error searching dialogs: {e}")
        return None

async def main():
    """Main function"""
    logger.info("🚀 Starting bot...")
    
    # Connect to Telegram
    await telegram_client.start()
    
    # Get user info
    me = await telegram_client.get_me()
    logger.info(f"✅ Logged in as: {me.first_name} (@{me.username})")
    
    # Method 1: Try to find channel by ID directly (may fail if not cached)
    try:
        channel = await telegram_client.get_entity(CHANNEL_ID)
        logger.info(f"✅ Connected to channel using ID: {channel.title}")
    except ValueError as e:
        logger.warning(f"⚠️ Could not find channel by ID directly: {e}")
        logger.warning("This is normal for first run or new channels.")
        
        # Method 2: Search through dialogs to find the channel
        channel = await find_channel()
        
        if not channel:
            logger.error("❌ Failed to find channel. Exiting.")
            return
        
        logger.info(f"✅ Successfully found and cached channel: {channel.title}")
    
    # Now that channel is found, set up the message handler specifically for this channel
    # Remove the generic handler and add a channel-specific one
    @telegram_client.on(events.NewMessage(chats=channel))
    async def channel_handler(event):
        await handle_signal(event)
    
    logger.info(f"👂 Listening for signals from: {channel.title}")
    logger.info("Bot is ready! Waiting for signals...")
    
    # Keep the bot running
    await telegram_client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
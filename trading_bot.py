import asyncio
import logging
import re
import math
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from binance.client import Client

# ========== YOUR CREDENTIALS ==========
API_ID = 38099889
API_HASH = "333fe09debc36b6aac46aa60dac30e30"
BINANCE_KEY = "ApgzC2cpewhBKqb1YPODfRCPzzV1Cy1y3wtpUiDAk8Dq21o6dFG4r6fcVpISey9W"
BINANCE_SECRET = "TllMkU490TyHO5HORsIF9QZsbgveitB2nb95CWgh39HbmOHz0GSJZnf9mlNa5r95"
CHANNEL_ID = -1002245575219
SESSION_STRING = "1BVtsOLsBu7-3Uaw0j6l5j0saUw58qhJ1cidZFrnw3lEI6nFRILffsW2gDtBX__8WaQZ0zkDRl3HtLs5DY9x-sbiHkJcoX1lXGcG7YDgTfXvqweasefhPC6Vp_F7itL6-LOd9pSueRJCxaNgA-VTNcA2PjfYBxejy7ueKpGD1b-ttjUIXEHX3J1gGPJKS47jMmNdcVN_b2x3JtcFO-nO35gRb1YMaDFfdJ_svj6bbP_hRZo3JLMs6ka31J9MGUMrJjKdQpmoMWMLKfnAeo3OP_kVs-lCFGTB8t7QQhMDqoeuxtDiXy6vBBmN_djpbTl7OSny2OoXbRGeG1Auxa_1fIn-_8a4gV-w="
# ======================================

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RISK_PERCENT = 1
active_positions = {}

def get_usdt_balance(client):
    """Get USDT balance from futures account"""
    try:
        balance = client.futures_account_balance()
        for item in balance:
            if item['asset'] == 'USDT':
                logger.info(f"💰 Balance: {item['balance']} USDT")
                return float(item['balance'])
        return 0
    except Exception as e:
        logger.error(f"Balance error: {e}")
        return 0

def calculate_quantity(entry_price, stop_loss, symbol, client):
    """Calculate position size based on 1% risk"""
    try:
        balance = get_usdt_balance(client)
        risk_amount = balance * (RISK_PERCENT / 100)
        logger.info(f"📊 Risk amount: {risk_amount} USDT")
        
        info = client.futures_exchange_info()
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
        
        precision = int(round(-math.log10(step_size)))
        quantity = math.floor(raw_quantity * (10 ** precision)) / (10 ** precision)
        
        logger.info(f"✅ Final quantity: {quantity}")
        return quantity
    except Exception as e:
        logger.error(f"Quantity error: {e}")
        return 0

def extract_symbol(text):
    """Extract symbol from message (e.g., CATI-USDT → CATIUSDT)"""
    match = re.search(r'([A-Z]+)-USDT', text, re.IGNORECASE)
    if match:
        return match.group(1).upper() + "USDT"
    return None

def close_position(symbol, client):
    """Close any open position for symbol"""
    try:
        # Cancel open orders
        client.futures_cancel_all_open_orders(symbol=symbol)
        logger.info(f"✅ Cancelled open orders for {symbol}")
        
        # Check and close position
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                side = 'SELL' if float(pos['positionAmt']) > 0 else 'BUY'
                quantity = abs(float(pos['positionAmt']))
                
                client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=quantity
                )
                logger.info(f"✅ Closed position for {symbol}")
                
                if symbol in active_positions:
                    del active_positions[symbol]
                return True
        return False
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return False

async def main():
    """Main async function"""
    logger.info("🚀 Starting bot...")
    
    # Initialize Telegram client
    telegram_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    # Initialize Binance client - NO PROXY, just like the first working bot
    try:
        binance_client = Client(BINANCE_KEY, BINANCE_SECRET, testnet=True)
        binance_client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'
        logger.info("✅ Binance client initialized")
        
        # Test connection
        balance = binance_client.futures_account_balance()
        logger.info("✅ Binance connection successful")
    except Exception as e:
        logger.error(f"❌ Binance connection failed: {e}")
        logger.error("Please check your API keys")
        return
    
    # Connect to Telegram
    await telegram_client.start()
    me = await telegram_client.get_me()
    logger.info(f"✅ Logged into Telegram as: {me.first_name}")
    
    # Find channel
    logger.info("🔍 Searching for your private channel...")
    channel = None
    async for dialog in telegram_client.iter_dialogs():
        if dialog.id == CHANNEL_ID:
            logger.info(f"✅ Found channel: {dialog.name}")
            channel = dialog.entity
            break
    
    if not channel:
        logger.error("❌ Channel not found! Make sure you are a member.")
        return
    
    @telegram_client.on(events.NewMessage(chats=channel))
    async def handler(event):
        try:
            text = event.message.text
            text_lower = text.lower()
            logger.info(f"📨 Signal received")
            
            # Check for close signal
            if any(word in text_lower for word in ["close the trade", "negative", "kindly close", "exit"]):
                logger.info("🔴 CLOSE SIGNAL DETECTED!")
                symbol = extract_symbol(text)
                if symbol:
                    logger.info(f"Closing position for {symbol}")
                    close_position(symbol, binance_client)
                return
            
            # Check for trade signal
            if 'usdt' not in text_lower or ('long' not in text_lower and 'short' not in text_lower):
                return
            
            logger.info(f"🎯 TRADE SIGNAL DETECTED!")
            
            # Extract data
            pair_match = re.search(r'([A-Z]+-USDT)', text, re.IGNORECASE)
            entry_match = re.search(r'Entry.*?(\d+\.?\d*)', text, re.IGNORECASE)
            sl_match = re.search(r'SL.*?(\d+\.?\d*)', text, re.IGNORECASE)
            tp1_match = re.search(r'TP1.*?(\d+\.?\d*)', text, re.IGNORECASE)
            lev_match = re.search(r'\((\d+)X\)', text, re.IGNORECASE)
            
            if not all([pair_match, entry_match, sl_match, tp1_match]):
                logger.warning("Missing required data")
                return
            
            symbol_raw = pair_match.group(1)
            symbol = symbol_raw.replace('-', '')
            entry_price = float(entry_match.group(1))
            stop_loss = float(sl_match.group(1))
            tp1 = float(tp1_match.group(1))
            side = 'BUY' if 'long' in text_lower else 'SELL'
            
            quantity = calculate_quantity(entry_price, stop_loss, symbol, binance_client)
            if quantity <= 0:
                return
            
            leverage = int(lev_match.group(1)) if lev_match else 2
            binance_client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"⚡ Leverage: {leverage}X")
            
            # Place main order
            binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                price=entry_price,
                quantity=quantity,
                timeInForce='GTC'
            )
            logger.info(f"✅ ORDER PLACED! Waiting for TP1 @ {tp1}")
            
            # Store position
            active_positions[symbol] = {
                'entry': entry_price,
                'sl': stop_loss,
                'tp1': tp1,
                'quantity': quantity,
                'side': side
            }
            
            # Place TP1 order (50%)
            tp1_side = 'SELL' if side == 'BUY' else 'BUY'
            binance_client.futures_create_order(
                symbol=symbol,
                side=tp1_side,
                type='LIMIT',
                price=tp1,
                quantity=quantity / 2,
                timeInForce='GTC'
            )
            logger.info(f"✅ TP1 order placed @ {tp1}")
            
            # Place stop loss
            sl_side = 'SELL' if side == 'BUY' else 'BUY'
            binance_client.futures_create_order(
                symbol=symbol,
                side=sl_side,
                type='STOP_MARKET',
                stopPrice=stop_loss,
                quantity=quantity,
                timeInForce='GTC'
            )
            logger.info(f"✅ Stop loss set @ {stop_loss}")
            
        except Exception as e:
            logger.error(f"Handler error: {e}")
    
    logger.info(f"👂 Listening for signals from: {channel.title}")
    logger.info("✅ Bot ready - Will auto-close trades on close signals")
    
    await telegram_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

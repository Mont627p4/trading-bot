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
    try:
        balance = client.futures_account_balance()
        for item in balance:
            if item['asset'] == 'USDT':
                return float(item['balance'])
        return 0
    except Exception as e:
        logger.error(f"Balance error: {e}")
        return 0

def calculate_quantity(entry_price, stop_loss, symbol, client):
    try:
        balance = get_usdt_balance(client)
        risk_amount = balance * (RISK_PERCENT / 100)
        
        info = client.futures_exchange_info()
        step_size = 0.001
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for filt in s['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        step_size = float(filt['stepSize'])
                        break
        
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            return 0
            
        raw_quantity = risk_amount / price_diff
        precision = int(round(-math.log10(step_size)))
        quantity = math.floor(raw_quantity * (10 ** precision)) / (10 ** precision)
        
        return quantity
    except Exception as e:
        logger.error(f"Quantity error: {e}")
        return 0

def extract_symbol(text):
    match = re.search(r'([A-Z]+)-USDT', text, re.IGNORECASE)
    if match:
        return match.group(1).upper() + "USDT"
    return None

def close_position(symbol, client):
    try:
        client.futures_cancel_all_open_orders(symbol=symbol)
        logger.info(f"✅ Cancelled orders for {symbol}")
        
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
                return True
        return False
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return False

async def main():
    logger.info("🚀 Starting bot...")
    
    telegram_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    # Initialize Binance client with forced URLs
    binance_client = Client(BINANCE_KEY, BINANCE_SECRET, testnet=True)
    binance_client.API_URL = 'https://testnet.binance.vision/api'
    binance_client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'
    logger.info("✅ Binance client ready")
    
    await telegram_client.start()
    me = await telegram_client.get_me()
    logger.info(f"✅ Logged in as: {me.first_name}")
    
    # Find channel
    channel = None
    async for dialog in telegram_client.iter_dialogs():
        if dialog.id == CHANNEL_ID:
            channel = dialog.entity
            logger.info(f"✅ Found channel: {dialog.name}")
            break
    
    if not channel:
        logger.error("❌ Channel not found!")
        return
    
    @telegram_client.on(events.NewMessage(chats=channel))
    async def handler(event):
        try:
            text = event.message.text
            text_lower = text.lower()
            logger.info(f"📨 Signal received")
            
            # Close signal
            if any(word in text_lower for word in ["close", "negative", "exit"]):
                logger.info("🔴 CLOSE SIGNAL")
                symbol = extract_symbol(text)
                if symbol:
                    close_position(symbol, binance_client)
                return
            
            # Trade signal
            if 'usdt' not in text_lower or ('long' not in text_lower and 'short' not in text_lower):
                return
            
            pair = re.search(r'([A-Z]+-USDT)', text, re.IGNORECASE)
            entry = re.search(r'Entry.*?(\d+\.?\d*)', text, re.IGNORECASE)
            sl = re.search(r'SL.*?(\d+\.?\d*)', text, re.IGNORECASE)
            tp1 = re.search(r'TP1.*?(\d+\.?\d*)', text, re.IGNORECASE)
            lev = re.search(r'\((\d+)X\)', text, re.IGNORECASE)
            
            if not all([pair, entry, sl, tp1]):
                return
            
            symbol = pair.group(1).replace('-', '')
            entry_price = float(entry.group(1))
            stop_loss = float(sl.group(1))
            tp1_price = float(tp1.group(1))
            side = 'BUY' if 'long' in text_lower else 'SELL'
            
            qty = calculate_quantity(entry_price, stop_loss, symbol, binance_client)
            if qty <= 0:
                return
            
            leverage = int(lev.group(1)) if lev else 2
            binance_client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            # Place orders
            binance_client.futures_create_order(
                symbol=symbol, side=side, type='LIMIT',
                price=entry_price, quantity=qty, timeInForce='GTC'
            )
            logger.info(f"✅ Order placed")
            
            # TP1
            tp1_side = 'SELL' if side == 'BUY' else 'BUY'
            binance_client.futures_create_order(
                symbol=symbol, side=tp1_side, type='LIMIT',
                price=tp1_price, quantity=qty/2, timeInForce='GTC'
            )
            
            # Stop loss
            sl_side = 'SELL' if side == 'BUY' else 'BUY'
            binance_client.futures_create_order(
                symbol=symbol, side=sl_side, type='STOP_MARKET',
                stopPrice=stop_loss, quantity=qty, timeInForce='GTC'
            )
            
        except Exception as e:
            logger.error(f"Handler error: {e}")
    
    logger.info("👂 Listening for signals...")
    await telegram_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

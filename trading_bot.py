from telethon import TelegramClient, events
from telethon.sessions import StringSession
from binance.client import Client
import re
import math
import asyncio
import logging

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

async def main():
    logger.info("🚀 Starting bot...")
    
    # Initialize clients INSIDE the async function
    telegram_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    binance_client = Client(BINANCE_KEY, BINANCE_SECRET, testnet=True)
    binance_client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'
    
    # Connect to Telegram
    await telegram_client.start()
    me = await telegram_client.get_me()
    logger.info(f"✅ Logged in as: {me.first_name}")
    
    # Find channel by searching dialogs
    logger.info("🔍 Searching for your private channel...")
    channel = None
    async for dialog in telegram_client.iter_dialogs():
        if dialog.id == CHANNEL_ID:
            logger.info(f"✅ Found channel: {dialog.name}")
            channel = dialog.entity
            break
    
    if not channel:
        logger.error("❌ Channel not found!")
        return
    
    @telegram_client.on(events.NewMessage(chats=channel))
    async def handler(event):
        try:
            text = event.message.text
            logger.info(f"📨 Signal received")
            
            # Extract data
            pair_match = re.search(r'([A-Z]+-USDT)', text, re.IGNORECASE)
            entry_match = re.search(r'Entry.*?(\d+\.?\d*)', text, re.IGNORECASE)
            sl_match = re.search(r'SL.*?(\d+\.?\d*)', text, re.IGNORECASE)
            tp1_match = re.search(r'TP1.*?(\d+\.?\d*)', text, re.IGNORECASE)
            lev_match = re.search(r'\((\d+)X\)', text, re.IGNORECASE)
            
            if not all([pair_match, entry_match, sl_match, tp1_match]):
                return
            
            symbol_raw = pair_match.group(1)
            symbol = symbol_raw.replace('-', '')
            entry_price = float(entry_match.group(1))
            stop_loss = float(sl_match.group(1))
            tp1 = float(tp1_match.group(1))
            side = 'BUY' if 'LONG' in text.upper() else 'SELL'
            
            # Place order
            leverage = int(lev_match.group(1)) if lev_match else 2
            binance_client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            binance_client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                price=entry_price,
                quantity=0.001,  # Small test quantity
                timeInForce='GTC'
            )
            logger.info(f"✅ ORDER PLACED!")
            
        except Exception as e:
            logger.error(f"Handler error: {e}")
    
    logger.info(f"👂 Listening for signals from: {channel.title}")
    await telegram_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

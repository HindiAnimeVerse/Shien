import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from shein_client import SheinClient

# Load environment variables
load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SHEIN_COOKIES = os.getenv("SHEIN_COOKIES")
ADMIN_ID = os.getenv("ADMIN_ID") # To send automatic notifications

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Silence verbose logs from external libraries
logging.getLogger("aiogram").setLevel(logging.WARNING)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
client = SheinClient(SHEIN_COOKIES)

# Track seen product codes to avoid duplicates
seen_products = set()

def get_admin_id():
    try:
        if ADMIN_ID:
            return int(ADMIN_ID)
    except:
        return ADMIN_ID
    return None

def format_product_message(product):
    name = product.get("name", "Unknown Product")
    # User wants the "real price" (usually in 'price' or 'wasPriceData')
    price = product.get("price", {}).get("displayformattedValue") or product.get("wasPriceData", {}).get("displayformattedValue", "N/A")
    
    msg = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 **SHEIN INDIA NEW DROP** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 **Name:** {name}\n"
        f"💵 **Price:** {price}\n\n"
        f"🚀 *Fastest Shein Checker Active*"
    )
    return msg

def get_product_keyboard(product_url):
    full_url = f"https://www.sheinindia.in{product_url}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 SHOP NOW", url=full_url)]
    ])
    return keyboard

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("🚀 **Shein India Men's Checker Bot is Active!**\n\nChecking `sverse-5939-37961` every 1 minute.")

@dp.message(Command("check"))
async def manual_check(message: types.Message):
    await message.reply("🔎 Running manual check...")
    products = await client.fetch_products()
    if not products:
        await message.reply("❌ No products found or error occurred.")
        return

    # Show first 3 for manual check
    for product in products[:3]:
        msg = format_product_message(product)
        image_url = product.get("images", [{}])[0].get("url")
        keyboard = get_product_keyboard(product.get("url", ""))
        
        if image_url:
            await message.answer_photo(photo=image_url, caption=msg, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await message.answer(msg, reply_markup=keyboard, parse_mode="Markdown")

async def monitor_task():
    global seen_products
    admin_id = get_admin_id()
    logging.info(f"Starting monitor task with Admin ID: {admin_id}")
    
    # Wait for bot to be ready
    await asyncio.sleep(2)
    
    if admin_id:
        try:
            startup_msg = (
                f"� **SHEIN MONITORING SYSTEM v2.0**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ **NETWORK:** Stabilized (Session-Based)\n"
                f"✅ **SSL/TLS:** Hardened (HTTP/1.1)\n"
                f"⏱ **LATENCY:** 1s (Ultra-Speed)\n"
                f"🎯 **TARGET:** Category Drops & Restocks\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 *System is now live and tracking changes...*"
            )
            await bot.send_message(chat_id=admin_id, text=startup_msg, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Could not send startup message to {admin_id}: {e}")

    # Initial run to populate seen_products and last_total
    initial_data = await client.fetch_page_0()
    last_total = 0
    seen_products = set()
    if initial_data:
        last_total = initial_data.get("pagination", {}).get("totalResults", 0)
        initial_products = await client.fetch_products()
        seen_products = {p.get("code") for p in initial_products if p.get("code")}
    
    logging.info(f"Monitor Initialized: {len(seen_products)} items, TotalResults={last_total}")

    while True:
        try:
            await asyncio.sleep(1) # 1-second precision check
            
            metadata = await client.fetch_page_0()
            if not metadata:
                continue
                
            current_total = metadata.get("pagination", {}).get("totalResults", -1)
            
            # Detect Change - Follow latest data exactly as per user request
            if current_total != -1 and current_total != last_total:
                # Perform audit
                products = await client.fetch_products()
                if not products:
                    # If fetch fails, don't update last_total yet
                    continue

                current_codes = {p.get("code") for p in products if p.get("code")}
                new_added = [p for p in products if p.get("code") and p.get("code") not in seen_products]
                
                # Snapshot-based delta tracking
                has_history = hasattr(monitor_task, 'last_snapshot')
                prev_snapshot = monitor_task.last_snapshot if has_history else current_codes
                removed_count = len(prev_snapshot - current_codes) if has_history else 0
                added_count = len(new_added)
                
                # ONLY notify if there is a REAL change in the product list
                if added_count > 0 or removed_count > 0:
                    # 1. Notify about New Items (Individual Alerts)
                    for p in new_added:
                        name = p.get("name", "New Item")
                        p_id = p.get("code")
                        img_url = p.get("images", [{}])[0].get("url")
                        url = f"https://www.sheinindia.in{p.get('url', '')}"
                        
                        caption = (
                            "🚀 **NEW SHEIN DROP DETECTED!** 🚀\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📦 **Item:** `{name}`\n"
                            f"🏷 **ID:** `{p_id}`\n"
                            f"💰 **Price:** `{p.get('price', {}).get('formattedValue', 'N/A')}`\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "💎 *Monitoring catalog for instant drops*"
                        )
                        
                        markup = InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text="🛒 View on Shein 🛒", url=url)
                        ]])

                        try:
                            if admin_id:
                                if img_url:
                                    await bot.send_photo(admin_id, img_url, caption=caption, reply_markup=markup, parse_mode="Markdown")
                                else:
                                    await bot.send_message(admin_id, caption, reply_markup=markup, parse_mode="Markdown")
                        except Exception as e:
                            logging.error(f"Failed to send drop alert: {e}")

                    # 2. Webhook for 100+ items (Only on REAL changes)
                    if len(current_codes) >= 100:
                        webhook_url = os.getenv("WEBHOOK_URL")
                        if webhook_url:
                            try:
                                import aiohttp
                                async with aiohttp.ClientSession() as session:
                                    payload = {
                                        "total": len(current_codes),
                                        "added": added_count,
                                        "removed": removed_count,
                                        "timestamp": int(asyncio.get_event_loop().time())
                                    }
                                    await session.post(webhook_url, json=payload, timeout=5)
                            except Exception as e:
                                logging.error(f"Webhook failed: {e}")

                    # 3. Send and PIN Summary Update
                    current_total_count = len(current_codes)
                    prev_total_count = len(prev_snapshot)
                    
                    summary_lines = [
                        "📢 **Shein Catalog Update**",
                        "━━━━━━━━━━━━━━━━━━━━━━",
                        f"📦 **Previous Total:** `{prev_total_count}`",
                        f"🆕 **Items Added:** `+{added_count}`",
                        f"📉 **Items Removed:** `-{removed_count}`" if removed_count > 0 else "📉 **Items Removed:** `0`",
                        f"📈 **Current Total:** `{current_total_count}`",
                        "━━━━━━━━━━━━━━━━━━━━━━"
                    ]
                    
                    summary_msg = "\n".join(summary_lines)
                    
                    if admin_id:
                        try:
                            sent_msg = await bot.send_message(admin_id, summary_msg, parse_mode="Markdown")
                            # Pin the latest summary
                            try:
                                await bot.pin_chat_message(admin_id, sent_msg.message_id)
                            except: pass
                        except Exception as e:
                            logging.error(f"Failed to send/pin summary: {e}")

                    logging.info(f"Audit Complete: Added={added_count}, Removed={removed_count}, CurrentCatalog={current_total_count}")
                
                # ALWAYS Finalize State to prevent being "stuck"
                last_total = current_total
                seen_products.update(current_codes)
                monitor_task.last_snapshot = current_codes

        except Exception as e:
            logging.error(f"Monitor loop error: {e}")
            await asyncio.sleep(2)

async def main():
    # Start a dummy web server for Hugging Face health checks
    port = int(os.getenv("PORT", 7860))
    from aiohttp import web
    async def handle(request): return web.Response(text="BOT_ACTIVE")
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    asyncio.create_task(site.start())
    logging.info(f"Health check server started on port {port}")

    # Network stability delay
    logging.info("Waiting 5 seconds for network to stabilize...")
    await asyncio.sleep(5)

    # Start monitoring in background
    asyncio.create_task(monitor_task())
    
    # Run bot polling with retry
    retry_count = 0
    while retry_count < 10:
        try:
            logging.info("Starting bot polling...")
            await dp.start_polling(bot)
            break
        except Exception as e:
            retry_count += 1
            logging.error(f"Polling failed (Attempt {retry_count}): {e}")
            await asyncio.sleep(10)
    
    # Final cleanup
    logging.info("Closing sessions...")
    await client.close()
    await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot manually stopped.")

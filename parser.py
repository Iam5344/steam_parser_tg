import asyncio
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

TELEGRAM_TOKEN = '7403885817:AAGt5YAv5dzFH0mQkFeRxWpwwP6FaLV_Z2w'
CHAT_ID = 5559159126
STEAM_CHECK_INTERVAL = 1800  # 30 minutes

parser_active = False
found_games = set()
bot_instance = None
executor = ThreadPoolExecutor(max_workers=2)


def parse_steam_sync():
    global found_games
    
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        print("Checking Steam...")
        driver.get("https://store.steampowered.com/search/?maxprice=free&supportedlang=russian&specials=1&ndl=1")
        time.sleep(5)
        
        games = driver.find_elements(By.CSS_SELECTOR, ".search_result_row")
        
        new_games = []
        message = f"Steam results from {datetime.now().strftime('%H:%M:%S')}:\n\n"
        
        for game in games:
            try:
                name = game.find_element(By.CSS_SELECTOR, ".title").text
                discount = game.find_element(By.CSS_SELECTOR, ".discount_pct").text
                
                if discount == "-100%" and name not in found_games:
                    found_games.add(name)
                    new_games.append(name)
                    message += f"Found: {name}\n"
                    print(f"Found game: {name}")
            except:
                continue
        
        driver.quit()
        return len(new_games) > 0, message
    
    except Exception as e:
        print(f"Error: {e}")
        return False, f"Error: {e}"


async def parse_steam():
    global bot_instance
    
    loop = asyncio.get_event_loop()
    found, message = await loop.run_in_executor(executor, parse_steam_sync)
    
    if found and bot_instance:
        await bot_instance.send_message(chat_id=CHAT_ID, text=message)
    elif not found:
        print("No new games found")


async def steam_parser_loop():
    global parser_active
    
    while parser_active:
        try:
            await parse_steam()
        except Exception as e:
            print(f"Error in parser loop: {e}")
        
        await asyncio.sleep(STEAM_CHECK_INTERVAL)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global parser_active
    
    if parser_active:
        await update.message.reply_text("Steam parser already running!")
        return
    
    parser_active = True
    await update.message.reply_text("Steam parser started! Checking Steam...")
    
    await parse_steam()
    
    asyncio.create_task(steam_parser_loop())
    await update.message.reply_text("Results will be sent every 5 minutes.")


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global parser_active, found_games
    
    if not parser_active:
        await update.message.reply_text("Steam parser is not running!")
        return
    
    parser_active = False
    found_games.clear()
    await update.message.reply_text("Steam parser stopped.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
STEAM PARSER

/start - Start parser (results every 30 min)
/stop - Stop parser
/help - This help
"""
    await update.message.reply_text(help_text)


async def post_init(application: Application):
    global bot_instance
    bot_instance = application.bot
    print("Steam parser bot started!")


def main():
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("help", help_command))
    
    print("Steam parser is running. Use /start to begin")
    application.run_polling()


if __name__ == '__main__':
    main()

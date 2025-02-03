import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
import yt_dlp
import logging

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Directory
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Search results cache
search_results_cache = {}

# Start command handler
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Welcome to the Music Bot! \ud83c\udfb6\n"
        "Send me the name of a song or artist to search for music."
    )

# Help command handler
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "How to use this bot:\n"
        "1. Send the name of a song or artist to search.\n"
        "2. Select a result from the search.\n"
        "3. Choose to either play or download the music.\n"
        "Supported formats: MP3.\n"
    )

# Search music on YouTube
async def search_music(update: Update, context: CallbackContext) -> None:
    query = update.message.text.strip()

    if not query:
        await update.message.reply_text("Please provide a search query.")
        return

    await update.message.reply_text(f"Searching for '{query}'... \ud83c\udfa7")

    try:
        # yt-dlp options for searching
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)['entries']

        if not search_results:
            await update.message.reply_text("No results found. Try another query.")
            return

       
        search_results_cache[update.message.chat_id] = search_results

      
        keyboard = [
            [
                InlineKeyboardButton(f"{i + 1}. {result['title']} - {result['duration_string']}",
                                     callback_data=f"play_{i}"),
                InlineKeyboardButton("Download", callback_data=f"download_{i}")
            ]
            for i, result in enumerate(search_results)
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a song from the results:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("An error occurred while searching.")


async def play_music(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id

    if chat_id not in search_results_cache:
        await query.answer("Search results expired. Please search again.")
        return

    # Get selected result
    index = int(query.data.split('_')[1])
    selected_result = search_results_cache[chat_id][index]
    url = selected_result['url']

    await query.answer("Streaming your selection... \ud83c\udfb6")
    await query.edit_message_text("Playing your selection... \ud83c\udfb6")

    try:
       
        await context.bot.send_audio(
            chat_id=chat_id,
            audio=url,
            title=selected_result['title'],
            performer=selected_result.get('uploader', 'Unknown'),
            duration=selected_result.get('duration'),
        )

        await query.message.reply_text("Now playing! \ud83c\udfb5")

    except Exception as e:
        logger.error(e)
        await query.message.reply_text("An error occurred while streaming the music.")

# Download selected audio
async def download_audio(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id

    if chat_id not in search_results_cache:
        await query.answer("Search results expired. Please search again.")
        return

    
    index = int(query.data.split('_')[1])
    selected_result = search_results_cache[chat_id][index]
    url = selected_result['url']

    await query.answer("Downloading your selection... \ud83c\udfb6")
    await query.edit_message_text("Downloading your selection... \ud83c\udfb6")

    try:
        # yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        # Download audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            audio_file = f"{os.path.splitext(file_path)[0]}.mp3"

        # Send audio to the user
        await context.bot.send_audio(chat_id, audio=open(audio_file, 'rb'))
        await query.message.reply_text("Here is your audio! \ud83c\udfb5")

        # Clean up
        os.remove(audio_file)

    except Exception as e:
        logger.error(e)
        await query.message.reply_text("An error occurred while downloading the music.")

async def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    action, index = query.data.split("_")

    if action == "play":
        await play_music(update, context)
    elif action == "download":
        await download_audio(update, context)

def main():
    TOKEN = "7641250686:AAE64T_Rsdyl-AwVAmxJ85Pgczkz6DWheRc"

    application = Application.builder().token(TOKEN).build()

    
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))

    
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()

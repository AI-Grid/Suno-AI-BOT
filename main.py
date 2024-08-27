import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

# Import Suno AI library
import suno

# Load environment variables from .env file
load_dotenv()

# Initialize Suno AI Library
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
client = suno.Suno(cookie=SUNO_COOKIE)

# Store user session data
chat_states = {}
password_attempts = {}  # To store successful password attempts

# Get bot settings from environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REQUIRED_CHAT_ID = os.getenv("REQUIRED_CHAT_ID")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the user is authorized
async def is_authorized(update: Update, context: CallbackContext) -> bool:
    """Check if the user is in the required chat or provides the correct password."""
    user_id = update.effective_user.id

    # Check if the user is in the required chat
    if update.effective_chat.id == int(REQUIRED_CHAT_ID):
        return True

    # Check if the user has already provided the correct password
    if user_id in password_attempts and password_attempts[user_id]:
        return True

    # Prompt for password
    await update.effective_user.send_message("🔒 Please provide the bot password to proceed:")

    def check_response(message: Update) -> bool:
        return message.effective_user.id == user_id and message.effective_chat.id == user_id

    try:
        # Wait for response in the chat
        response = await context.bot.wait_for("message", timeout=60, check=check_response)
        if response.text.lower() == BOT_PASSWORD:
            password_attempts[user_id] = True
            await response.effective_user.send_message("✅ Password accepted! You can now use the bot.")
            return True
        else:
            await response.effective_user.send_message("❌ Incorrect password.")
            return False
    except asyncio.TimeoutError:
        await update.effective_user.send_message("⏰ Timeout. You did not provide the password in time.")
        return False

# Command to handle /start or /help
async def help_command(update: Update, context: CallbackContext) -> None:
    help_message = (
        "👋 Hello! Welcome to the *Suno AI Music Generator Bot*! 🎶\n\n"
        "👉 Use /help to show this basic information 🎶\n\n"
        "👉 Use /generate to start creating your unique music track. 🚀\n"
        "📥 I was made by [Marty](https://main.easierit.org). This bot utilizes the [SunoAI API](https://github.com/Malith-Rukshan/Suno-API)."
    )
    await update.message.reply_text(help_message)

# Command to start music generation
async def generate(update: Update, context: CallbackContext) -> None:
    if not await is_authorized(update, context):
        return

    user_id = update.effective_user.id
    chat_states[user_id] = {}
    await update.message.reply_text('Select mode: custom or not. 🤔\nType "custom" or "default".')

# Command to cancel the generation process
async def stop(update: Update, context: CallbackContext) -> None:
    if not await is_authorized(update, context):
        return

    user_id = update.effective_user.id
    if user_id in chat_states:
        del chat_states[user_id]  # Clear the user's state
        await update.message.reply_text('Generation canceled. 🚫 You can start again with /generate.')
    else:
        await update.message.reply_text('No active session to cancel. 🚫')

# Message handler for mode selection and input collection
async def message_handler(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id in chat_states:
        msg_content = update.message.text.strip()

        if 'mode' not in chat_states[user_id]:
            if msg_content.lower() == "custom":
                chat_states[user_id]['mode'] = 'custom'
                await update.message.reply_text("🎤 Send lyrics first.")
            elif msg_content.lower() == "default":
                chat_states[user_id]['mode'] = 'default'
                await update.message.reply_text("🎤 Send song description.")
            return

        if 'lyrics' not in chat_states[user_id]:
            chat_states[user_id]['lyrics'] = msg_content
            await update.message.reply_text("📝 Please provide a title for your song.")
            return

        if 'title' not in chat_states[user_id]:
            chat_states[user_id]['title'] = msg_content
            if chat_states[user_id]['mode'] == 'custom':
                chat_states[user_id]['tags'] = "Wait-for-tags"
                await update.message.reply_text("🏷️ Now send tags.\n\nExample: Classical")
            else:
                await generate_music(update, context)
            return

        if chat_states[user_id]['mode'] == 'custom' and chat_states[user_id]['tags'] == "Wait-for-tags":
            chat_states[user_id]['tags'] = msg_content
            await generate_music(update, context)

# Function to generate music
async def generate_music(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    await update.message.reply_text("Generating your music... please wait. ⏳")
    try:
        prompt = chat_states[user_id]['lyrics']
        is_custom = chat_states[user_id]['mode'] == 'custom'
        tags = chat_states[user_id].get('tags', None)
        title = chat_states[user_id].get('title', 'generated_music')  # Default title if not provided

        # Generate Music
        songs = await asyncio.to_thread(
            client.generate,
            prompt=prompt,
            tags=tags if is_custom else None,
            is_custom=is_custom,
            wait_audio=True
        )

        for index, song in enumerate(songs):
            file_path = await asyncio.to_thread(client.download, song=song)

            # Construct the new file name using the title and index
            new_file_path = f"{title}_v{index + 1}.mp3"
            os.rename(file_path, new_file_path)

            # Send the file to Telegram
            await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(new_file_path, 'rb'), title=title)

            # Remove the file after sending
            os.remove(new_file_path)

        chat_states.pop(user_id, None)
    except Exception as e:
        await update.message.reply_text(f"⁉️ Failed to generate music: {e}")
        chat_states.pop(user_id, None)

# Main function to start the bot
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", help_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("generate", generate))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    await application.start_polling()
    await application.idle()

if __name__ == "__main__":
    asyncio.run(main())

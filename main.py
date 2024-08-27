import os
import asyncio
from dotenv import load_dotenv
from rocketchat_API.rocketchat import RocketChat

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
ROCKET_CHAT_URL = os.getenv("ROCKET_CHAT_URL")
ROCKET_CHAT_USER = os.getenv("ROCKET_CHAT_USER")
ROCKET_CHAT_PASSWORD = os.getenv("ROCKET_CHAT_PASSWORD")
REQUIRED_ROOM = os.getenv("REQUIRED_ROOM")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")

# Initialize Rocket.Chat client
rocket = RocketChat(ROCKET_CHAT_USER, ROCKET_CHAT_PASSWORD, server_url=ROCKET_CHAT_URL)

async def is_authorized(user_id, room_id):
    """Check if the user provides the correct password or is in the correct room."""
    if room_id != REQUIRED_ROOM:
        return False
    if user_id in password_attempts and password_attempts[user_id]:
        return True

    rocket.chat_post_message(
        "🔒 Please provide the bot password to proceed:",
        room_id=room_id
    )

    def check_response(message):
        return message['u']['_id'] == user_id and message['rid'] == room_id

    try:
        # Wait for response in the chat
        response = await wait_for_message(user_id)
        if response.lower() == BOT_PASSWORD:
            password_attempts[user_id] = True
            rocket.chat_post_message(
                "✅ Password accepted! You can now use the bot.",
                room_id=room_id
            )
            return True
        else:
            rocket.chat_post_message(
                "❌ Incorrect password.",
                room_id=room_id
            )
            return False
    except asyncio.TimeoutError:
        rocket.chat_post_message(
            "⏰ Timeout. You did not provide the password in time.",
            room_id=room_id
        )
        return False

async def wait_for_message(user_id):
    """Wait for the user's response in the chat."""
    while True:
        messages = rocket.channels_history(REQUIRED_ROOM).json()['messages']
        for message in messages:
            if message['u']['_id'] == user_id:
                return message['msg']
        await asyncio.sleep(1)

async def message_handler(message):
    user_id = message['u']['_id']
    room_id = message['rid']
    msg_content = message['msg'].strip()

    # Handle !help command (no authorization required)
    if msg_content.startswith('!help'):
        help_message = (
            "👋 Hello! Welcome to the *Suno AI Music Generator Bot*! 🎶\n\n"
            "👉 Use !help to show this basic information 🎶\n\n"
            "👉 Use !generate to start creating your unique music track. 🚀\n"
            "📥 I was made by [Marty](https://main.easierit.org). This bot utilizes the [SunoAI API](https://github.com/Malith-Rukshan/Suno-API)."
        )
        rocket.chat_post_message(help_message, room_id=room_id)
        return

    # Handle !generate command
    if msg_content.startswith('!generate'):
        if not await is_authorized(user_id, room_id):
            return

        rocket.chat_post_message(
            'Select mode: custom or not. 🤔\nType "custom" or "default".',
            room_id=room_id
        )
        chat_states[user_id] = {}
        return

    # Continue with music generation process
    if user_id in chat_states:
        if 'mode' not in chat_states[user_id]:
            if msg_content.lower() == "custom":
                chat_states[user_id]['mode'] = 'custom'
                rocket.chat_post_message("🎤 Send lyrics first.", room_id=room_id)
            elif msg_content.lower() == "default":
                chat_states[user_id]['mode'] = 'default'
                rocket.chat_post_message("🎤 Send song description.", room_id=room_id)
            return

        if 'lyrics' not in chat_states[user_id]:
            chat_states[user_id]['lyrics'] = msg_content
            rocket.chat_post_message("📝 Please provide a title for your song.", room_id=room_id)
            return

        if 'title' not in chat_states[user_id]:
            chat_states[user_id]['title'] = msg_content
            if chat_states[user_id]['mode'] == 'custom':
                chat_states[user_id]['tags'] = "Wait-for-tags"
                rocket.chat_post_message("🏷️ Now send tags.\n\nExample: Classical", room_id=room_id)
            else:
                await generate_music(user_id, room_id)
            return

        if chat_states[user_id]['mode'] == 'custom' and chat_states[user_id]['tags'] == "Wait-for-tags":
            chat_states[user_id]['tags'] = msg_content
            await generate_music(user_id, room_id)

async def generate_music(user_id, room_id):
    rocket.chat_post_message("Generating your music... please wait. ⏳", room_id=room_id)
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
            
            # Upload the file to Rocket.Chat
            rocket.chat_upload(new_file_path, room_id=room_id, description=new_file_path)
            
            # Remove the file after sending
            os.remove(new_file_path)

        chat_states.pop(user_id, None)
    except Exception as e:
        rocket.chat_post_message(f"⁉️ Failed to generate music: {e}", room_id=room_id)
        chat_states.pop(user_id, None)

async def main():
    while True:
        messages = rocket.channels_history(REQUIRED_ROOM).json()['messages']
        for message in reversed(messages):
            await message_handler(message)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

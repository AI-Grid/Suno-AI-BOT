import os
import asyncio
from dotenv import load_dotenv
import nio

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
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
MATRIX_USER = os.getenv("MATRIX_USER")
MATRIX_PASSWORD = os.getenv("MATRIX_PASSWORD")
REQUIRED_ROOM = os.getenv("REQUIRED_ROOM")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")

# Initialize the Matrix client
matrix_client = nio.AsyncClient(MATRIX_HOMESERVER, MATRIX_USER)

async def is_authorized(room: nio.MatrixRoom, event: nio.RoomMessageText):
    """Check if the user provides the correct password or is in the correct room."""
    if room.room_id != REQUIRED_ROOM:
        return False
    if event.sender in password_attempts and password_attempts[event.sender]:
        return True

    await matrix_client.room_send(
        room_id=event.room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "🔒 Please provide the bot password to proceed:"
        }
    )

    def check_response(e):
        return isinstance(e, nio.RoomMessageText) and e.sender == event.sender

    try:
        response = await matrix_client.sync_forever(timeout=60000, full_state=True)
        if response.content['body'] == BOT_PASSWORD:
            password_attempts[event.sender] = True
            await matrix_client.room_send(
                room_id=event.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": "✅ Password accepted! You can now use the bot."
                }
            )
            return True
        else:
            await matrix_client.room_send(
                room_id=event.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": "❌ Incorrect password."
                }
            )
            return False
    except asyncio.TimeoutError:
        await matrix_client.room_send(
            room_id=event.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": "⏰ Timeout. You did not provide the password in time."
            }
        )
        return False

# Handling text messages
@matrix_client.event_listener(nio.RoomMessageText)
async def message_handler(room: nio.MatrixRoom, event: nio.RoomMessageText):
    if event.sender == matrix_client.user_id:
        return

    # Handle !help command (no authorization required)
    if event.body.lower().startswith('!help'):
        help_message = (
            "👋 Hello! Welcome to the *Suno AI Music Generator Bot*! 🎶\n\n"
            "👉 Use !help to show this basic information 🎶\n\n"
            "👉 Use !generate to start creating your unique music track. 🚀\n"
            "📥 I was made by [Marty](https://main.easierit.org). This bot utilizes the [SunoAI API](https://github.com/Malith-Rukshan/Suno-API)."
        )
        await matrix_client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": help_message
            }
        )
        return

    # Handle !generate command
    if event.body.lower().startswith('!generate'):
        if not await is_authorized(room, event):
            return

        await matrix_client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": 'Select mode: custom or not. 🤔\nType "custom" or "default".'
            }
        )
        chat_states[event.sender] = {}
        return

    # Continue with music generation process
    user_id = event.sender
    if user_id in chat_states:
        if 'mode' not in chat_states[user_id]:
            if event.body.lower() == "custom":
                chat_states[user_id]['mode'] = 'custom'
                await matrix_client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": "🎤 Send lyrics first."
                    }
                )
            elif event.body.lower() == "default":
                chat_states[user_id]['mode'] = 'default'
                await matrix_client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": "🎤 Send song description."
                    }
                )
            return

        if 'lyrics' not in chat_states[user_id]:
            chat_states[user_id]['lyrics'] = event.body
            await matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": "📝 Please provide a title for your song."
                }
            )
            return

        if 'title' not in chat_states[user_id]:
            chat_states[user_id]['title'] = event.body
            if chat_states[user_id]['mode'] == 'custom':
                chat_states[user_id]['tags'] = "Wait-for-tags"
                await matrix_client.room_send(
                    room_id=room.room_id,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": "🏷️ Now send tags.\n\nExample: Classical"
                    }
                )
            else:
                await generate_music(event, room)
            return

        if chat_states[user_id]['mode'] == 'custom' and chat_states[user_id]['tags'] == "Wait-for-tags":
            chat_states[user_id]['tags'] = event.body
            await generate_music(event, room)

async def generate_music(event, room):
    user_id = event.sender
    await matrix_client.room_send(
        room_id=room.room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "Generating your music... please wait. ⏳"
        }
    )
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
            
            # Upload the file to Matrix
            await matrix_client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.file",
                    "filename": new_file_path,
                    "body": new_file_path,
                }
            )
            
            # Remove the file after sending
            os.remove(new_file_path)

        chat_states.pop(user_id, None)
    except Exception as e:
        await matrix_client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": f"⁉️ Failed to generate music: {e}"
            }
        )
        chat_states.pop(user_id, None)

# Log in and run the bot
async def main():
    await matrix_client.login(MATRIX_PASSWORD)
    await matrix_client.sync_forever(timeout=30000)

asyncio.run(main())

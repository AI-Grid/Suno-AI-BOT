import os
import logging
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
import suno

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Suno AI Library
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
client = suno.Suno(cookie=SUNO_COOKIE)

# Store user session data
chat_states = {}
password_attempts = {}

# Get bot settings from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_ROLE = os.getenv("REQUIRED_ROLE")

# Intents and bot initialization
intents = discord.Intents.all()
intents.messages = True
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Read users.txt and store user data
user_data = {}
with open('users.txt', 'r') as file:
    for line in file:
        if ':' in line:
            username, password, limit = line.strip().split(':')
            user_data[username] = {'password': password, 'limit': int(limit)}

async def is_authorized(ctx):
    """Check if the user is in the users list and has provided the correct password."""
    
    username = ctx.author.name

    if username not in user_data:
        await ctx.author.send("---Identification not recognized by system---\n---Connection Terminated---")
        return False

    # Always ask for a password in each session
    if ctx.author.id in password_attempts:
        del password_attempts[ctx.author.id]

    # If the command is issued in a DM, skip the role check and go straight to password protection
    if isinstance(ctx.channel, discord.DMChannel):
        return await check_password(ctx)
    
    # If the command is issued in a guild (server), check the role
    if REQUIRED_ROLE:
        roles = [role.strip() for role in REQUIRED_ROLE.split(',')]
        if any(discord.utils.get(ctx.guild.roles, name=role) in ctx.author.roles for role in roles):
            return await check_password(ctx)

    return await check_password(ctx)

async def check_password(ctx):
    """Check if the user has provided the correct password and is within their usage limit."""
    username = ctx.author.name
    user_info = user_data.get(username)

    if not user_info:
        await ctx.author.send("---Identification not recognized by system---\n---Connection Terminated---")
        return False

    correct_password = user_info['password']
    usage_limit = user_info['limit']

    if usage_limit == 0:
        await ctx.author.send("❌ You have reached your usage limit.")
        return False

    await ctx.author.send("🔒 Please provide your password to proceed:")

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        response = await bot.wait_for('message', check=check, timeout=60.0)
        if response.content == correct_password:
            password_attempts[ctx.author.id] = True
            await ctx.author.send("✅ Password accepted! You can now use the bot.")
            return True
        else:
            await ctx.author.send("❌ Incorrect password.")
            return False
    except asyncio.TimeoutError:
        await ctx.author.send("⏳ Timeout. You did not provide the password in time.")
        return False

# Update usage limit after successful generation
def update_usage_limit(username):
    if username in user_data:
        if user_data[username]['limit'] > 0:
            user_data[username]['limit'] -= 1

        # Save the updated limit back to the file
        with open('users.txt', 'w') as file:
            for user, data in user_data.items():
                file.write(f"{user}:{data['password']}:{data['limit']}\n")

# Remove discord default help command
bot.remove_command('help')

# Help message
@bot.command(name='help')
async def help_command(ctx):
    help_message = (
        "👋 Hello! Welcome to the *Suno AI Music Generator Bot*! 🎶\n\n"
        "👉 Use !help to show this basic help information 🎵\n\n"
        "👉 Use !generate to start creating your unique music track. (Remember you need rank or password) 🎤\n"
        "👉 Use !stop to cancel all and clear memory to start over 🎧\n"
        "🛠️ I was made by [Marty](https://main.easierit.org). You can take own hosted version from [AI-Grid Github](https://github.com/AI-Grid/Suno-AI-BOT-discord/) This bot utilizes the [SunoAI API](https://github.com/Malith-Rukshan/Suno-API)."
    )
    await ctx.send(help_message)

# Command to start music generation
@bot.command(name='generate')
async def generate(ctx):
    if not await is_authorized(ctx):
        return

    await ctx.send('Select mode: custom or not. 🤔\nType "custom" or "default".')
    chat_states[ctx.author.id] = {}

# Command to stop and clear state
@bot.command(name='stop')
async def stop(ctx):
    user_id = ctx.author.id
    if user_id in chat_states:
        del chat_states[user_id]  # Clear the user's state
        await ctx.send('Generation stopped. 🚫 You can start again with !generate.')
    else:
        await ctx.send('No active session to stop. 🚫')

# Message handler for mode selection and input collection
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = message.author.id
    
    # Always check if !stop command was issued
    if message.content.lower() == "!stop":
        await stop(message)
        await message.channel.send('Sesja została pomyślnie przerwana. Możesz zacząć od nowa za pomocą !generate.')
        return

    if user_id in chat_states:
        if 'mode' not in chat_states[user_id]:
            if message.content.lower() == "custom":
                chat_states[user_id]['mode'] = 'custom'
                await message.channel.send("🎤 Send lyrics first.")
            elif message.content.lower() == "default":
                chat_states[user_id]['mode'] = 'default'
                await message.channel.send("🎤 Send song description.")
            return

        if 'lyrics' not in chat_states[user_id]:
            chat_states[user_id]['lyrics'] = message.content
            await message.channel.send("🎼 Please provide a title for your song.")
            return

        if 'title' not in chat_states[user_id]:
            chat_states[user_id]['title'] = message.content
            if chat_states[user_id]['mode'] == 'custom':
                chat_states[user_id]['tags'] = "Wait-for-tags"
                await message.channel.send("🎹 Now send tags.\n\nExample: Classical")
            else:
                await generate_music(message)
            return

        if chat_states[user_id]['mode'] == 'custom' and chat_states[user_id]['tags'] == "Wait-for-tags":
            chat_states[user_id]['tags'] = message.content
            await generate_music(message)

    await bot.process_commands(message)

async def generate_music(message):
    user_id = message.author.id
    username = message.author.name

    await message.channel.send("Generating your music... please wait. 🎶")
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
            
            # Upload the file to Discord
            await message.channel.send(file=discord.File(new_file_path, filename=new_file_path))
            
            # Remove the file after sending
            os.remove(new_file_path)

        # Decrement usage limit if not unlimited (-1)
        if user_data[username]['limit'] != -1:
            update_usage_limit(username)

        chat_states.pop(user_id, None)
        await message.channel.send("Thank you for using the bot! 🎧")
    except Exception as e:
        await message.channel.send(f"❗ Failed to generate music: {e}")
        chat_states.pop(user_id, None)

# Run the bot
bot.run(BOT_TOKEN)

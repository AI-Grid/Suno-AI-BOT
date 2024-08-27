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
password_attempts = {}  # To store successful password attempts

# Get bot settings from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_ROLE = os.getenv("REQUIRED_ROLE")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")

# Intents and bot initialization
intents = discord.Intents.all()
intents.messages = True
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

async def is_authorized(ctx):
    """Check if the user has the required role or provides the correct password."""
    
    # If the command is issued in a DM, skip the role check and go straight to password protection
    if isinstance(ctx.channel, discord.DMChannel):
        return await check_password(ctx)
    
    # If the command is issued in a guild (server), check the role
    if REQUIRED_ROLE:
        role = discord.utils.get(ctx.guild.roles, name=REQUIRED_ROLE)
        if role in ctx.author.roles:
            return True
    
    # Prompt for password in DM if not authorized by role
    return await check_password(ctx)

async def check_password(ctx):
    """Check if the user has provided the correct password."""
    # Check if user has already provided the correct password
    if ctx.author.id in password_attempts and password_attempts[ctx.author.id]:
        return True

    # Prompt for password in DM
    await ctx.author.send("🔒 Please provide the bot password to proceed:")

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        response = await bot.wait_for('message', check=check, timeout=60.0)
        if response.content == BOT_PASSWORD:
            password_attempts[ctx.author.id] = True
            await ctx.author.send("✅ Password accepted! You can now use the bot.")
            return True
        else:
            await ctx.author.send("❌ Incorrect password.")
            return False
    except asyncio.TimeoutError:
        await ctx.author.send("⏰ Timeout. You did not provide the password in time.")
        return False

# Welcome message
@bot.command(name='start')
async def start(ctx):
    if not await is_authorized(ctx):
        return

    welcome_message = (
        "👋 Hello! Welcome to the *Suno AI Music Generator Bot*! 🎶\n\n"
        "👉 Use !generate to start creating your unique music track. 🚀\n"
        "📥 Bot was made by [Marty](https://main.easierit.org). This bot utilizes the [SunoAI API](https://github.com/Malith-Rukshan/Suno-API)."
    )
    await ctx.send(welcome_message)

# Command to check credits
@bot.command(name='credits')
async def credits_command(ctx):
    if not await is_authorized(ctx):
        return

    credit_info_message = (
        "**💰Credits Stat**\n\n"
        "ᗚ Available : {}\n"
        "ᗚ Usage : {}"
    )
    try:
        credits = await asyncio.to_thread(client.get_credits)
    except Exception as e:
        return await ctx.send(f"⁉️ Failed to get credits info: {e}")
    await ctx.send(credit_info_message.format(credits.credits_left, credits.monthly_usage))

# Command to start music generation
@bot.command(name='generate')
async def generate(ctx):
    if not await is_authorized(ctx):
        return

    await ctx.send('Select mode: custom or not. 🤔\nType "custom" or "default".')
    chat_states[ctx.author.id] = {}

# Command to cancel and clear state
@bot.command(name='cancel')
async def cancel(ctx):
    if not await is_authorized(ctx):
        return

    user_id = ctx.author.id
    if user_id in chat_states:
        del chat_states[user_id]  # Clear the user's state
        await ctx.send('Generation canceled. 🚫 You can start again with !generate.')
    else:
        await ctx.send('No active session to cancel. 🚫')

# Message handler for mode selection and input collection
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = message.author.id
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
            await message.channel.send("📝 Please provide a title for your song.")
            return

        if 'title' not in chat_states[user_id]:
            chat_states[user_id]['title'] = message.content
            if chat_states[user_id]['mode'] == 'custom':
                chat_states[user_id]['tags'] = "Wait-for-tags"
                await message.channel.send("🏷️ Now send tags.\n\nExample: Classical")
            else:
                await generate_music(message)
            return

        if chat_states[user_id]['mode'] == 'custom' and chat_states[user_id]['tags'] == "Wait-for-tags":
            chat_states[user_id]['tags'] = message.content
            await generate_music(message)

    await bot.process_commands(message)

async def generate_music(message):
    user_id = message.author.id
    await message.channel.send("Generating your music... please wait. ⏳")
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

        chat_states.pop(user_id, None)
    except Exception as e:
        await message.channel.send(f"⁉️ Failed to generate music: {e}")
        chat_states.pop(user_id, None)

# Run the bot
bot.run(BOT_TOKEN)

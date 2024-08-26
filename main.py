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

# Intents and bot initialization
intents = discord.Intents.all()
intents.messages = True
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Welcome message
@bot.command(name='start')
async def start(ctx):
    welcome_message = (
        "👋 Hello! Welcome to the *Suno AI Music Generator Bot*! 🎶\n\n"
        "👉 Use !generate to start creating your unique music track. 🚀\n"
        "👉 Use !credits to check your credits balance.\n\n"
        "📥 This bot utilizes the [SunoAI API](https://github.com/Malith-Rukshan/Suno-API)."
    )
    await ctx.send(welcome_message)

# Command to check credits
@bot.command(name='credits')
async def credits_command(ctx):
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
    await ctx.send('Select mode: custom or not. 🤔\nType "custom" or "default".')
    chat_states[ctx.author.id] = {}

# Command to cancel and clear state
@bot.command(name='cancel')
async def cancel(ctx):
    user_id = ctx.author.id
    if user_id in chat_states:
        chat_states.pop(user_id, None)
    await ctx.send('Generation canceled. 🚫 You can start again with !generate.')

# Message handler for mode selection and input collection
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = message.author.id
    if user_id in chat_states and 'mode' not in chat_states[user_id]:
        if message.content.lower() == "custom":
            chat_states[user_id]['mode'] = 'custom'
            await message.channel.send("🎤 Send lyrics first.")
        elif message.content.lower() == "default":
            chat_states[user_id]['mode'] = 'default'
            await message.channel.send("🎤 Send song description.")
        return

    if user_id in chat_states and 'mode' in chat_states[user_id]:
        if 'lyrics' not in chat_states[user_id]:
            chat_states[user_id]['lyrics'] = message.content
            if chat_states[user_id]['mode'] == 'custom':
                chat_states[user_id]['tags'] = "Wait-for-tags"
                await message.channel.send("🏷️ Now send tags.\n\nExample: Classical")
            else:
                await generate_music(message)
        elif chat_states[user_id]['mode'] == 'custom' and chat_states[user_id]['tags'] == "Wait-for-tags":
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

        # Generate Music
        songs = await asyncio.to_thread(
            client.generate,
            prompt=prompt,
            tags=tags if is_custom else None,
            is_custom=is_custom,
            wait_audio=True
        )

        for song in songs:
            file_path = await asyncio.to_thread(client.download, song=song)
            await message.channel.send(file=discord.File(file_path, filename="generated_music.mp3"))
            os.remove(file_path)

        chat_states.pop(user_id, None)
    except Exception as e:
        await message.channel.send(f"⁉️ Failed to generate music: {e}")
        chat_states.pop(user_id, None)

# Run the bot
bot.run(os.getenv("BOT_TOKEN"))

import os
import logging
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
import suno
from flask import Flask, jsonify, render_template, request, redirect, url_for, send_from_directory
from datetime import datetime, timedelta
import shutil

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
flask_port =  os.getenv("port")
# Intents and bot initialization
intents = discord.Intents.all()
intents.messages = True
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Load users from users.txt
def load_user_data():
    user_data = {}
    with open('users.txt', 'r') as file:
        for line in file:
            if ':' in line:
                username, password, limit = line.strip().split(':')
                user_data[username] = {'password': password, 'limit': int(limit)}
    return user_data

# Save users to users.txt
def save_user_data(user_data):
    with open('users.txt', 'w') as file:
        for user, data in user_data.items():
            file.write(f"{user}:{data['password']}:{data['limit']}\n")

# Update usage limit after successful generation
def update_usage_limit(username):
    if username in user_data:
        if user_data[username]['limit'] > 0:
            user_data[username]['limit'] -= 1

        # Update the `users.txt` file with the new limit
        save_user_data(user_data)

# Flask application
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['ADMIN_SECRET_KEY'] = os.getenv('ADMIN_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'downloads'

# Homepage route
@app.route('/')
def home():
    return render_template('index.html')

# Status check route
@app.route('/status')
def status():
    return jsonify({"status": "Bot is running"})

# Manage Users route
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    user_data = load_user_data()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        limit = request.form['limit']

        if username and password and limit:
            user_data[username] = {'password': password, 'limit': int(limit)}
            save_user_data(user_data)
            return redirect(url_for('manage_users'))

    return render_template('users.html', user_data=user_data)

# Manage Files route
@app.route('/files', methods=['GET'])
def manage_files():
    music_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.mp3')]
    return render_template('files.html', files=music_files)

# Clear Files route
@app.route('/clear_files', methods=['POST'])
def clear_files():
    days = int(request.form.get('days', 30))
    cutoff_date = datetime.now() - timedelta(days=days)

    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mod_time < cutoff_date:
                os.remove(file_path)

    return redirect(url_for('manage_files'))

# Route to delete a file
@app.route('/delete_file/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('manage_files'))
    except Exception as e:
        return str(e), 500

# Route to download a file
@app.route('/download_file/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Discord bot functions
def load_authorized_users():
    authorized_users = set()
    try:
        with open('owners.txt', 'r') as file:
            for line in file:
                user_id = line.strip()
                if user_id.isdigit():
                    authorized_users.add(user_id)
    except FileNotFoundError:
        print("owners.txt file not found.")
    return authorized_users

authorized_users = load_authorized_users()
user_data = load_user_data()

async def is_authorized(ctx):
    username = ctx.author.name

    if username not in user_data:
        await ctx.author.send("---Identification not recognized by system---\n---Connection Terminated---")
        return False

    if ctx.author.id in password_attempts:
        del password_attempts[ctx.author.id]

    if isinstance(ctx.channel, discord.DMChannel):
        return await check_password(ctx)
    
    if REQUIRED_ROLE:
        roles = [role.strip() for role in REQUIRED_ROLE.split(',')]
        if any(discord.utils.get(ctx.guild.roles, name=role) in ctx.author.roles for role in roles):
            return await check_password(ctx)

    return await check_password(ctx)

async def check_password(ctx):
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
        del chat_states[user_id]
        await ctx.send('Generation stopped. 🚫 You can start again with !generate.')
    else:
        await ctx.send('No active session to stop. 🚫')

@bot.command(name='reload_users')
async def reload_users(ctx):
    """Reload the user data from users.txt without restarting the bot and display the current limits."""
    
    global authorized_users
    authorized_users = load_authorized_users()

    if str(ctx.author.id) not in authorized_users:
        await ctx.send("⛔ You do not have permission to use this command.")
        return

    global user_data
    user_data = load_user_data()
    response_message = "🔄 User data has been reloaded. Here are the current limits:\n"

    for username, data in user_data.items():
        limit_display = "Unlimited" if data['limit'] == -1 else f"{data['limit']} remaining"
        response_message += f"**{username}**: {limit_display}\n"

    await ctx.send(response_message)

# Message handler for mode selection and input collection
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = message.author.id
    
    # Always check if !stop command was issued
    if message.content.lower() == "!stop":
        await stop(message)
        await message.channel.send('Session successfully terminated. You can start again with !generate.')
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
        title = chat_states[user_id].get('title', 'generated_music')

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
            new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{title}_v{index + 1}.mp3")
            os.rename(file_path, new_file_path)
            
            # Upload the file to Discord
            await message.channel.send(file=discord.File(new_file_path, filename=os.path.basename(new_file_path)))
            
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

# Run the Flask and Discord bot applications
if __name__ == "__main__":
    from threading import Thread

    # Run Flask app in a separate thread
    def run_flask():
        app.run(host='0.0.0.0', port=flask_port)

    # Start Flask app
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Start Discord bot
    bot.run(BOT_TOKEN)

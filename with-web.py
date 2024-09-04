import os
import time
import configparser
from flask import Flask, request, redirect, url_for, render_template, flash, send_file, session
from threading import Thread
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import suno

# Load environment variables from .env file
load_dotenv()

# Flask app setup
app = Flask(__name__)

# Load configuration from config.txt
config = configparser.ConfigParser()
config.read('config.txt')

# Apply configurations from config.txt
flask_port = int(config['FLASK']['port'])
app.secret_key = config['FLASK']['secret_key']
admin_secret_key = config['FLASK']['admin_secret_key']  # Add this in config.txt

# Directory for generated files
DOWNLOADS_DIR = 'downloads'
USERS_FILE = 'users.txt'

# Intents and bot initialization
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize Suno AI Library
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
client = suno.Suno(cookie=SUNO_COOKIE)

# Store user session data
chat_states = {}
password_attempts = {}
AUTHORIZED_USERS = {}

def load_users():
    """Load authorized users from a file."""
    global AUTHORIZED_USERS
    AUTHORIZED_USERS = {}
    try:
        with open(USERS_FILE, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                username, credentials = line.split(':', 1)
                password, limit = credentials.split(':', 1)
                AUTHORIZED_USERS[username] = {'password': password, 'limit': int(limit), 'usage': 0}
    except FileNotFoundError:
        pass

load_users()  # Load users on startup

# Helper function to check if the user is authorized
def is_authorized(user_id):
    if user_id in AUTHORIZED_USERS:
        user_data = AUTHORIZED_USERS[user_id]
        if user_data['limit'] == -1 or user_data['usage'] < user_data['limit']:
            return True
    return False

# Helper function to track and enforce usage limits
def track_usage(user_id):
    if user_id in AUTHORIZED_USERS:
        AUTHORIZED_USERS[user_id]['usage'] += 1

# Helper function to reset usage limits
def reset_usage(user_id):
    if user_id in AUTHORIZED_USERS:
        AUTHORIZED_USERS[user_id]['usage'] = 0

# Helper function to get list of files in the download directory
def list_files(directory):
    files = []
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            files.append({
                'name': filename,
                'size': os.path.getsize(file_path),
                'mtime': time.ctime(os.path.getmtime(file_path))
            })
    return files

# Helper function to clear old files in the download directory
def clear_old_files(directory, days=1):
    current_time = time.time()
    removed_files = []
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > days * 86400:  # Days to seconds
                os.remove(file_path)
                removed_files.append(filename)
    return removed_files

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

# Route to show list of files in the download directory
@app.route('/files')
def files():
    if 'authenticated' not in session:
        return redirect(url_for('login'))

    file_list = list_files(DOWNLOADS_DIR)
    return render_template('files.html', files=file_list)

# Route to clear old files in the download directory
@app.route('/clear_files', methods=['POST'])
def clear_files():
    if 'authenticated' not in session:
        return redirect(url_for('login'))

    days = int(request.form.get('days', 1))
    removed_files = clear_old_files(DOWNLOADS_DIR, days)
    flash(f'Removed {len(removed_files)} files older than {days} days.')
    return redirect(url_for('files'))

# Route to download a specific file
@app.route('/download/<filename>')
def download_file(filename):
    if 'authenticated' not in session:
        return redirect(url_for('login'))

    file_path = os.path.join(DOWNLOADS_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found.')
        return redirect(url_for('files'))

# Route to view and edit users.txt
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if 'authenticated' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        action = request.form.get('action')
        user_data = request.form.get('user_data')
        new_limit = request.form.get('new_limit')

        if action == 'add':
            with open(USERS_FILE, 'a') as f:
                f.write(f"\n{user_data}")
            flash('User added successfully.')
        elif action == 'delete':
            with open(USERS_FILE, 'r') as f:
                users = f.readlines()
            with open(USERS_FILE, 'w') as f:
                for line in users:
                    if user_data not in line:
                        f.write(line)
            flash('User deleted successfully.')
        elif action == 'edit':
            username, password = user_data.split(':')[:2]
            updated = False
            with open(USERS_FILE, 'r') as f:
                users = f.readlines()
            with open(USERS_FILE, 'w') as f:
                for line in users:
                    if line.startswith(f"{username}:{password}:"):
                        f.write(f"{username}:{password}:{new_limit}\n")
                        updated = True
                    else:
                        f.write(line)
            if updated:
                flash('User limit updated successfully.')
            else:
                flash('User not found or invalid data.')

    with open(USERS_FILE, 'r') as f:
        users = f.readlines()

    return render_template('users.html', users=users)

# Login route to authenticate with the admin secret key
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        entered_key = request.form.get('secret_key')
        if entered_key == admin_secret_key:
            session['authenticated'] = True
            return redirect(url_for('files'))
        else:
            flash('Invalid secret key')

    return render_template('login.html')

# Logout route to clear the session
@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

# Discord command to reload users.txt
@bot.command(name='reload_users')
async def reload_users(ctx):
    if str(ctx.author) == "tinycopy":  # Assuming tinycopy is the bot owner
        load_users()
        await ctx.send("Users reloaded.")
    else:
        await ctx.send("You are not authorized to perform this action.")

# Command to start music generation
@bot.command(name='generate')
async def generate(ctx):
    if not is_authorized(str(ctx.author)):
        await ctx.send("You have reached your usage limit or are not authorized.")
        return

    track_usage(str(ctx.author))  # Track usage before proceeding

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
                await message.channel.send(f"Working on '{chat_states[user_id]['title']}' 🎧")
                await generate_music(message, user_id)

            return

        if 'tags' not in chat_states[user_id]:
            chat_states[user_id]['tags'] = message.content
            await message.channel.send(f"Working on '{chat_states[user_id]['title']}' with tags {chat_states[user_id]['tags']} 🎧")
            await generate_music(message, user_id)
            return

    await bot.process_commands(message)

# Function to generate music with Suno AI
async def generate_music(message, user_id):
    user_data = chat_states[user_id]
    mode = user_data['mode']
    lyrics = user_data['lyrics']
    title = user_data['title']
    tags = user_data.get('tags', None)

    if mode == 'custom':
        result = client.generate_custom_music(lyrics, title, tags)
    else:
        result = client.generate_default_music(title, lyrics)

    file_path = os.path.join(DOWNLOADS_DIR, f"{title}.mp3")
    with open(file_path, 'wb') as f:
        f.write(result)

    await message.channel.send(f"Your music is ready! Download it here: {file_path}")
    del chat_states[user_id]  # Clear state after completion

# Flask app running in a thread
def run_flask():
    app.run(host="0.0.0.0", port=flask_port)

# Start the Flask app in a separate thread
flask_thread = Thread(target=run_flask)
flask_thread.start()

# Start the Discord bot
TOKEN = os.getenv('BOT_TOKEN')
bot.run(TOKEN)

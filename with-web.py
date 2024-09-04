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
                AUTHORIZED_USERS[username] = (password, int(limit))
    except FileNotFoundError:
        pass

load_users()  # Load users on startup

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files')
def files():
    if 'authenticated' not in session:
        return redirect(url_for('login'))

    file_list = list_files(DOWNLOADS_DIR)
    return render_template('files.html', files=file_list)

@app.route('/clear_files', methods=['POST'])
def clear_files():
    if 'authenticated' not in session:
        return redirect(url_for('login'))

    days = int(request.form.get('days', 1))
    removed_files = clear_old_files(DOWNLOADS_DIR, days)
    flash(f'Removed {len(removed_files)} files older than {days} days.')
    return redirect(url_for('files'))

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

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@bot.command(name='reload_users')
async def reload_users(ctx):
    if is_authorized(str(ctx.author)):
        load_users()  # Reload users from the file
        with open(USERS_FILE, 'r') as f:
            users = f.readlines()
        await ctx.send(f"Users reloaded:\n" + ''.join(users))
    else:
        await ctx.send("You are not authorized to perform this action.")

@bot.command(name='generate')
async def generate(ctx):
    if not is_authorized(str(ctx.author)):  # Remove 'await'
        await ctx.send('You are not authorized to perform this action.')
        return

    await ctx.send('Select mode: custom or not. 🤔\nType "custom" or "default".')
    chat_states[ctx.author.id] = {}

@bot.command(name='stop')
async def stop(ctx):
    user_id = ctx.author.id
    if user_id in chat_states:
        del chat_states[user_id]  # Clear the user's state
        await ctx.send('Generation stopped. 🚫 You can start again with !generate.')
    else:
        await ctx.send('No active session to stop. 🚫')
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
                await generate_music(message)
            return

        if chat_states[user_id]['mode'] == 'custom' and chat_states[user_id]['tags'] == "Wait-for-tags":
            chat_states[user_id]['tags'] = message.content
            await generate_music(message)

    await bot.process_commands(message)

async def generate_music(message):
    user_id = message.author.id
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
            new_file_path = os.path.join(DOWNLOADS_DIR, f"{title}_v{index + 1}.mp3")
            os.rename(file_path, new_file_path)
            
            # Upload the file to Discord
            await message.channel.send(file=discord.File(new_file_path, filename=new_file_path))
            
            # Remove the file after sending
            # os.remove(new_file_path)

        chat_states.pop(user_id, None)
        await message.channel.send("Thank you for using the bot! 🎧")
    except Exception as e:
        await message.channel.send(f"❗ Failed to generate music: {e}")
        chat_states.pop(user_id, None)

# Flask authentication helper
async def is_authorized(ctx):
    """Check if the user is in the users list and has provided the correct password."""
    
    # Reload user data before each authorization check
    load_user_data()

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


# Run Flask app in a separate thread
def run_flask():
    app.run(host='0.0.0.0', port=flask_port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(os.getenv("BOT_TOKEN"))

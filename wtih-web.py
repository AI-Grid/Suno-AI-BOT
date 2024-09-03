import os
import asyncio
from flask import Flask, request, redirect, url_for, render_template, flash
import discord
from discord.ext import commands
from threading import Thread
import configparser

# Load configuration from config.txt
config = configparser.ConfigParser()
config.read('config.txt')

# Flask app setup
app = Flask(__name__)

# Apply configurations from config.txt
flask_port = int(config['FLASK']['port'])
app.secret_key = config['FLASK']['secret_key']

# File paths
USERS_FILE = 'users.txt'

# Discord bot setup
intents = discord.Intents.all()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load authorized users
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

# Load users from file
def load_users():
    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as file:
            for line in file:
                if ':' in line:
                    username, password, limit = line.strip().split(':')
                    limit_display = "Unlimited" if int(limit) == -1 else f"{limit} remaining"
                    users.append({'username': username, 'password': password, 'limit': limit_display})
    return users

# Flask routes
@app.route('/')
def index():
    return render_template('index.html', users=load_users())

@app.route('/add', methods=['POST'])
def add_user():
    if not is_authorized(request.form.get('username')):
        flash('Unauthorized user')
        return redirect(url_for('index'))

    username = request.form['username']
    password = request.form['password']
    limit = request.form['limit']

    with open(USERS_FILE, 'a') as file:
        file.write(f"{username}:{password}:{limit}\n")

    flash(f'Added user {username}')
    return redirect(url_for('index'))

@app.route('/remove', methods=['POST'])
def remove_user():
    if not is_authorized(request.form.get('username')):
        flash('Unauthorized user')
        return redirect(url_for('index'))

    username_to_remove = request.form['username']

    with open(USERS_FILE, 'r') as file:
        lines = file.readlines()

    with open(USERS_FILE, 'w') as file:
        for line in lines:
            if not line.startswith(f"{username_to_remove}:"):
                file.write(line)

    flash(f'Removed user {username_to_remove}')
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update_user():
    if not is_authorized(request.form.get('username')):
        flash('Unauthorized user')
        return redirect(url_for('index'))

    username = request.form['username']
    new_limit = request.form['limit']

    with open(USERS_FILE, 'r') as file:
        lines = file.readlines()

    with open(USERS_FILE, 'w') as file:
        user_found = False
        for line in lines:
            if line.startswith(f"{username}:"):
                user_found = True
                username, password, _ = line.strip().split(':')
                file.write(f"{username}:{password}:{new_limit}\n")
            else:
                file.write(line)

    if user_found:
        flash(f'Updated limit for user {username}')
    else:
        flash(f'User {username} not found')

    return redirect(url_for('index'))

# Authorization check function for Flask
def is_authorized(username):
    return username in authorized_users

# Discord bot commands
@bot.command(name='reload_users')
async def reload_users(ctx):
    """Reload the user data from users.txt without restarting the bot and display the current limits."""
    global authorized_users
    authorized_users = load_authorized_users()

    if str(ctx.author.id) not in authorized_users:
        await ctx.send("⛔ You do not have permission to use this command.")
        return

    global user_data
    user_data = {}
    response_message = "🔄 User data has been reloaded. Here are the current limits:\n"

    with open(USERS_FILE, 'r') as file:
        for line in file:
            if ':' in line:
                username, password, limit = line.strip().split(':')
                user_data[username] = {'password': password, 'limit': int(limit)}
                
                limit_display = "Unlimited" if int(limit) == -1 else f"{limit} remaining"
                response_message += f"**{username}**: {limit_display}\n"

    await ctx.send(response_message)

# Run Flask app in a separate thread
def run_flask():
    app.run(port=flask_port)

# Start both Flask and Discord bot
if __name__ == "__main__":
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Run the Discord bot
    bot.run('YOUR_DISCORD_BOT_TOKEN')

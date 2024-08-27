from flask import Flask, request, jsonify
import os
import asyncio
import suno

app = Flask(__name__)

# Initialize Suno AI Library
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
client = suno.Suno(cookie=SUNO_COOKIE)

# Define your API key
API_KEY = os.getenv("API_KEY")

def check_api_key(key):
    return key == API_KEY

@app.route('/generate', methods=['POST'])
async def generate_music():
    api_key = request.headers.get('X-API-KEY')
    if not check_api_key(api_key):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    prompt = data.get('input')
    mode = data.get('mode', 'default')  # 'custom' or 'default'
    tags = data.get('tags', None) if mode == 'custom' else None

    if not prompt:
        return jsonify({'error': 'Missing input text'}), 400

    try:
        # Generate Music
        songs = await asyncio.to_thread(
            client.generate,
            prompt=prompt,
            tags=tags,
            is_custom=(mode == 'custom'),
            wait_audio=True
        )

        file_paths = []
        for song in songs:
            file_path = await asyncio.to_thread(client.download, song=song)
            file_paths.append(file_path)

        return jsonify({'files': file_paths})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)

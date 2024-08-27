from flask import Flask, request, jsonify
import os
import asyncio
import suno

app = Flask(__name__)

# Initialize Suno AI Library
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
client = suno.Suno(cookie=SUNO_COOKIE)

@app.route('/generate', methods=['POST'])
async def generate_music():
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

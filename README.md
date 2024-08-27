# 🎵 Suno AI Music Generator Discord Bot

Welcome to the Suno AI Music Generator Bot! 🤖 This bot leverages the [Suno AI API](https://github.com/Malith-Rukshan/Suno-API) to generate custom music tracks based on user inputs directly within Discord Server/DM.

✍️ Note : This is a **Very Basic Bot Example** demonstrating how to use the [Suno AI API](https://github.com/Malith-Rukshan/Suno-API).

[![PyPI Package](https://img.shields.io/badge/PyPi-Library-1cd760?logo=pypi&style=flat)](https://pypi.org/project/SunoAI/)
[![Suno-AI Github](https://img.shields.io/badge/Github-Suno--API-blue?logo=github&style=flat)](https://github.com/Malith-Rukshan/Suno-API)

## 🌟 Features

- **🎶 Music Generation**: Generate music by providing custom lyrics or a description.
- **🖱️ Interactive Commands**: Simple commands to start music generation, check credits, and cancel ongoing operations.
- **👥 Simple Interface**: Easy to use with inline buttons for quick selections.

## 🚀 Deployment
[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/AI-Grid/Suno-AI-BOT-discord/)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/AI-Grid/Suno-AI-BOT-discord/)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)
### 🔧 Prerequisites

- A registered Discord Bot Token (obtain one from [Discord Dev Page](https://discord.com/developers/applications/)
- Access to Suno AI API with a valid cookie - [Tutorial](https://github.com/Malith-Rukshan/Suno-API/tree/main?tab=readme-ov-file#-prerequisites)

### On PasS

Set `SUNO_COOKIE` and `BOT_TOKEN` as Environmental variables. Remember also to add `REQUIRED_ROLE` for your server and `BOT_PASSWORD` for authentication on dm
so example
```bash
BOT_TOKEN=your_discord_bot_token_here
SUNO_COOKIE=your_suno_cookie_here
REQUIRED_ROLE=YourRoleName
BOT_PASSWORD=your_secure_password
 ```
### Locally

1. **Clone the repository:**

    ```bash
    mkdir suno-bot && cd suno-bot
    git clone https://github.com/AI-Grid/Suno-AI-BOT-discord .
    
    ```

2. **Install required packages:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Set Environment Variables:**

    Set the `BOT_TOKEN` and `SUNO_COOKIE` in your environment variables or directly in the code.
    change your .env file:
    ```bash
   BOT_TOKEN='your_bot_token_here'
   SUNO_COOKIE='your_suno_cookie_here'
   REQUIRED_ROLE='YourRoleName'
   BOT_PASSWORD='your_secure_password'
    ```

4. **Run the Bot:**

    ```bash
    python main.py
    ```

## ⌨️ Commands

Interact with your bot on Telegram using the following commands:

- `!start` - Welcome message and basic bot information.
- `!generate` - Starts the music generation process.
- `!cancel` - Cancels the current operation and resets the session.

## 🤝 Contributing

Contributions to the Suno AI Music Generator Bot are welcome! Please feel free to fork the repository, make changes, and submit pull requests.

## 🎯 Credits and Other
All content and music generated through this bot are credited to [Suno AI](https://suno.ai/). This Bot by unofficial API provides a convenient way to interact with Suno AI's services but does not claim any ownership or rights over the music generated. Please respect  the terms of service of Suno AI when using their platform ❤️.

> This bot is intended primarily for educational and development purposes. It aims to enhance and simplify access to Suno AI's music generation capabilities. If you enjoy the music generated, consider supporting Suno AI directly.
> Based on Suno Telegram Bot by [@MalithRukshan](https://t.me/MalithRukshan)

## ⚖️ License
This project is distributed under the MIT License. This license allows everyone to use, modify, and redistribute the code. However, it comes with no warranties regarding its functionality. For more details, see the [LICENSE](https://github.com/Malith-Rukshan/Suno-API/blob/main/LICENSE) file in the repository.

## 🌟 Support and Community
If you found this project helpful, **don't forget to give it a ⭐ on GitHub.** This helps others find and use the project too! 🫶

Join our Telegram channels, 

- [@SingleDevelopers](https://t.me/SingleDevelopers), for more amazing projects and updates ✓
- [@SunoAPI](https://t.me/SunoAPI), for this project updates ✓

## 📬 Contact
If you have any questions, feedback, or just want to say hi, you can reach out to me:

- Original Developer : [@MalithRukshan](https://t.me/MalithRukshan)
- Me : [Martynka Adamski](https://my.secondlife.com/martynka.adamski)
- Suno AI Support Group on Telegram : [@Suno_API](https://t.me/Suno_API)

🧑‍💻 Redesigned by [💖Martynka Adamski💖](https://my.secondlife.com/martynka.adamski) originaly Built with 💖 for Telegram by [Single Developers </> ](https://t.me/SingleDevelopers)

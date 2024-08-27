from dotenv import load_dotenv
import os
import suno

# Load environment variables from the .env file
load_dotenv()

# Initialize Suno AI Library
SUNO_COOKIE = os.getenv("SUNO_COOKIE")
client = suno.Suno(cookie=SUNO_COOKIE)

def get_credits_info():
    try:
        # Get credits info
        credits_info = client.get_credits()
        print(f"💰 Credits Information:")
        print(f"ᗚ Available: {credits_info.credits_left}")
        print(f"ᗚ Usage: {credits_info.monthly_usage}")
    except Exception as e:
        print(f"⁉️ Failed to get credits info: {e}")

if __name__ == "__main__":
    get_credits_info()

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("FREELLMAPI_API_KEY"),
    base_url="http://localhost:3001/v1"
)

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_api_key = os.getenv("FREELLMAPI_API_KEY")

client = (
    OpenAI(
        api_key=_api_key,
        base_url="http://localhost:3001/v1"
    )
    if _api_key
    else None
)


def get_client():
    if client is None:
        raise RuntimeError(
            "FREELLMAPI_API_KEY is not configured. "
            "Check your .env file."
        )
    return client

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()
GEMINI_KEY = os.getenv("API_KEY")
MODEL = os.getenv("BASE_MODEL")
client = genai.Client(api_key=GEMINI_KEY)

_DIR = Path(__file__).parent

with open(_DIR / "soul.md", "r") as file:
    soul = file.read()

SYSTEM_PROMPT = f"""
You are the author of a childrens story 
{soul}
"""


class Story(BaseModel):
    title: str = Field(description="The title of the story")
    summary: str = Field(description="An overview of the story for the back cover")
    pages: list[str] = Field(
        description="A list of 4 strings. Each string is a page of the story."
    )


def generate_story(prompt: list) -> Story:
    with open(_DIR / "characters.md", "r") as file:
        characters = file.read()

    prompt = f"write a story about {characters}"
    story_response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Story,
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    return story_response.parsed


def run():
    story = generate_story(SYSTEM_PROMPT)

    return story

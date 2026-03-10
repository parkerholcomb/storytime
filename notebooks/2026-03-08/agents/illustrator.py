import os
import io
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path

from .author import Story
from IPython.display import display

load_dotenv()
GEMINI_KEY = os.getenv("API_KEY")
client = genai.Client(api_key=GEMINI_KEY)

_DIR = Path(__file__).parent

with open(_DIR / "soul.md", "r") as file:
    soul = file.read()

SYSTEM_PROMPT = f"""
You are the illustrator for a childrens story 
{soul}
"""


class Illustrations(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    characters: Image.Image = Field(description="The characters image of the book")
    front: Image.Image = Field(description="The cover image of the book")
    back: Image.Image = Field(description="The back cover image of the book")
    pages: list[Image.Image] = Field(description="The illustrations for the book")

    def display(self):
        display(self.characters)
        display(self.front)

        for page in self.pages:
            display(page)
        display(self.back)


def generate_image(
    contents: list, model: str = "gemini-3.1-flash-image-preview"
) -> Image:
    image_response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            system_instruction=SYSTEM_PROMPT,
            image_config=types.ImageConfig(
                aspect_ratio="3:2",
            ),
        ),
    )
    # print(image_response)
    img_data = image_response.candidates[0].content.parts[0].inline_data.data
    img = Image.open(io.BytesIO(img_data))
    return img


def generate_characters_image(story: Story) -> Image:
    with open(_DIR / "characters.md", "r") as file:
        characters = file.read()
    prompt = f"""
    here are the characters: {characters}
    here is the story: {story.model_dump_json()}

    draw just the characters, no background.
    these will be used throughout the story.

    now draw the characters in the story as an image.
    """
    return generate_image(prompt)


def generate_illustration(page: str, characters: Image) -> Image:
    return generate_image(
        [
            f"""
    now draw an illustration for this page of the book.

    page text: {page}

    draw the text on the illustration exactly. make sure to not hallucinate and use the exact copy. 

    also including the characters in the prompt as an image. 

    """,
            characters,
        ]
    )


def generate_cover_image(story: Story, characters: Image) -> Image:
    return generate_image(
        [
            f"""
     draw a cover for a book named: {story.title}

    here is the summary: {story.summary}

    draw the title on the illustration exactly. make sure to not hallucinate and use the exact copy. 

    also including the characters in the prompt as an image. 

    """,
            characters,
        ]
    )


def generate_back_cover_image(story: Story, characters: Image) -> Image:
    return generate_image(
        [
            f"""
     draw a back cover for a book named: {story.title}

    here is the summary: {story.summary}

    draw the title on the illustration exactly. make sure to not hallucinate and use the exact copy. 

    also including the characters in the prompt as an image. 

    """,
            characters,
        ]
    )


def run(story: Story) -> Illustrations:
    characters = generate_characters_image(story)
    front = generate_cover_image(story, characters)
    back = generate_back_cover_image(story, characters)
    illustrations = [generate_illustration(p, characters) for p in story.pages]
    return Illustrations(
        characters=characters, front=front, back=back, pages=illustrations
    )

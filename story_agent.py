import io
import os
import wave
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

load_dotenv()
GEMINI_KEY = os.getenv("API_KEY")
client = genai.Client(api_key=GEMINI_KEY)

fp = "soul.md"
with open(fp, "r") as file:
    soul = file.read()

SYSTEM_PROMPT = f"""
You are creating a childrens story 
{soul}
"""


class Story(BaseModel):
    title: str = Field(description="The title of the story")
    summary: str = Field(description="An overview of the story for the back cover")
    pages: list[str] = Field(
        description="A list of 4 strings. Each string is a page of the story."
    )


def generate_story(contents: list, model: str = "gemini-3.1-pro-preview") -> Story:
    story_response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Story,
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    return story_response.parsed


def generate_image(contents: list, model: str = "gemini-3-pro-image-preview") -> Image:
    image_response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    # print(image_response)
    img_data = image_response.candidates[0].content.parts[0].inline_data.data
    img = Image.open(io.BytesIO(img_data))
    return img


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

    draw the title on the illustration exactly. title should be the only text on the cover.

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

    

    also including the characters in the prompt as an image. 

    """,
            characters,
        ]
    )


def generate_audio(story: Story):
    full_story_text = " ".join(story.pages)
    tts_prompt = f"""
    Read the following children's story in a warm, playful, and enthusiastic tone:

    {full_story_text}
    """

    audio_response = client.models.generate_content(
        model="gemini-2.5-pro-preview-tts",
        contents=tts_prompt,
        config=types.GenerateContentConfig(
            # Tell the API to return audio instead of text
            response_modalities=["AUDIO"],
            # Optional: Select a specific voice (e.g., "Aoede", "Puck", "Kore")
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
                )
            ),
        ),
    )

    # 4. Extract the raw bytes
    pcm_data = audio_response.candidates[0].content.parts[0].inline_data.data

    # 5. Save it as a WAV file
    # The Gemini TTS API outputs 16-bit PCM audio at 24kHz
    audio_filename = f"output/{story.title}.wav"
    with wave.open(audio_filename, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(24000)  # 24kHz
        wf.writeframes(pcm_data)

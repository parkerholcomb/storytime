import os
import time
from pathlib import Path
from .author import Story
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from pydub import AudioSegment
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()
GEMINI_KEY = os.getenv("API_KEY")
client = genai.Client(api_key=GEMINI_KEY)
TTS_MODEL = os.getenv("TTS_MODEL")


_DIR = Path(__file__).parent

with open(_DIR / "soul.md", "r") as file:
    soul = file.read()

SYSTEM_PROMPT = f"""
You are the reader of a childrens story
{soul}
"""


class Narration(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    audio: AudioSegment = Field(description="The full narration audio")


MAX_RETRIES = 3
RETRY_BACKOFF = 5  # seconds


def generate_audio(story: Story) -> AudioSegment:
    full_story_text = " ".join(story.pages)
    tts_prompt = f"""
    Read the following children's story in a warm, playful, and enthusiastic tone:

    {full_story_text}
    """

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            audio_response = client.models.generate_content(
                model=TTS_MODEL,
                contents=tts_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    system_instruction=SYSTEM_PROMPT,
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
                        )
                    ),
                ),
            )
            break
        except ServerError as e:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF * attempt
            print(f"  ⚠ TTS server error (attempt {attempt}/{MAX_RETRIES}), retrying in {wait}s…")
            time.sleep(wait)

    pcm_data = audio_response.candidates[0].content.parts[0].inline_data.data
    return AudioSegment(
        data=pcm_data,
        sample_width=2,
        frame_rate=24000,
        channels=1,
    )


def run(story: Story) -> Narration:
    audio = generate_audio(story)
    return Narration(audio=audio)

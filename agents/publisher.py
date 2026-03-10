import io
import os
import re
from datetime import datetime

from PIL import Image
from google.cloud import storage
from .author import Story
from .illustrator import Illustrations
from .reader import Narration
from pydantic import BaseModel, Field

GCP_BUCKET_NAME = "storytime-share"
GCP_PUBLIC_BASE = f"https://storage.googleapis.com/{GCP_BUCKET_NAME}"


class Publication(BaseModel):
    title: str = Field(description="The title of the story")
    book_url: str = Field(description="The public URL of the published book PDF")
    audio_url: str = Field(description="The public URL of the narration audio")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _upload_bytes(bucket, path: str, data: bytes, content_type: str):
    blob = bucket.blob(path)
    blob.upload_from_string(data, content_type=content_type)


def _image_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _audio_bytes(audio) -> bytes:
    buf = io.BytesIO()
    audio.export(buf, format="mp3")
    return buf.getvalue()


def _to_rgb(img) -> Image.Image:
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        return background
    return img.convert("RGB")


def _build_pdf(illustrations: Illustrations) -> bytes:
    pages = [_to_rgb(illustrations.front)]
    for page_img in illustrations.pages:
        pages.append(_to_rgb(page_img))
    pages.append(_to_rgb(illustrations.back))

    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()


_PUBLICATIONS_MD = os.path.join(os.path.dirname(__file__), "publications.md")
_ROOT_README = os.path.join(os.path.dirname(__file__), "..", "README.md")


def _save_publication(pub: Publication, summary: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    catalog_entry = (
        f"\n## {pub.title}\n\n"
        f"*Published {timestamp}*\n\n"
        f"{summary}\n\n"
        f"- [Book (PDF)]({pub.book_url})\n"
        f"- [Narration (MP3)]({pub.audio_url})\n"
    )
    with open(_PUBLICATIONS_MD, "a") as f:
        f.write(catalog_entry)

    readme_entry = (
        f"\n### {pub.title}\n\n"
        f"*Published {timestamp}*\n\n"
        f"{summary}\n\n"
        f"- [Book (PDF)]({pub.book_url})\n"
        f"- [Narration (MP3)]({pub.audio_url})\n"
    )
    with open(_ROOT_README, "a") as f:
        f.write(readme_entry)


def run(
    story: Story, illustrations: Illustrations, narration: Narration
) -> Publication:
    client = storage.Client()
    bucket = client.bucket(GCP_BUCKET_NAME)
    prefix = _slugify(story.title)

    _upload_bytes(
        bucket,
        f"{prefix}/story.json",
        story.model_dump_json().encode(),
        "application/json",
    )
    _upload_bytes(
        bucket,
        f"{prefix}/characters.png",
        _image_bytes(illustrations.characters),
        "image/png",
    )
    _upload_bytes(
        bucket, f"{prefix}/front.png", _image_bytes(illustrations.front), "image/png"
    )
    _upload_bytes(
        bucket, f"{prefix}/back.png", _image_bytes(illustrations.back), "image/png"
    )

    for i, page_img in enumerate(illustrations.pages, 1):
        _upload_bytes(
            bucket, f"{prefix}/page_{i}.png", _image_bytes(page_img), "image/png"
        )

    pdf_data = _build_pdf(illustrations)
    pdf_path = f"{prefix}/book.pdf"
    _upload_bytes(bucket, pdf_path, pdf_data, "application/pdf")

    audio_path = f"{prefix}/narration.mp3"
    _upload_bytes(bucket, audio_path, _audio_bytes(narration.audio), "audio/mpeg")

    pub = Publication(
        title=story.title,
        book_url=f"{GCP_PUBLIC_BASE}/{pdf_path}",
        audio_url=f"{GCP_PUBLIC_BASE}/{audio_path}",
    )
    _save_publication(pub, story.summary)
    return pub

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents import author, illustrator, reader, publisher

MODELS = {
    "flash": {
        "BASE_MODEL": "gemini-3-flash-preview",
        "IMAGE_MODEL": "gemini-3.1-flash-image-preview",
        "TTS_MODEL": "gemini-2.5-flash-preview-tts",
    },
    "pro": {
        "BASE_MODEL": "gemini-3.1-pro-preview",
        "IMAGE_MODEL": "gemini-3-pro-image-preview",
        "TTS_MODEL": "gemini-2.5-pro-preview-tts",
    },
}


def configure_models():
    choice = input("Model tier — (1) flash  (2) pro: ").strip()
    tier = "pro" if choice == "2" else "flash"
    for key, value in MODELS[tier].items():
        os.environ[key] = value
    print(f"  → models set to {tier}")


def main():
    configure_models()
    t0 = time.time()

    print("Step 1/4 — Writing the story...")
    story: author.Story = author.run()
    print(f'  ✓ "{story.title}" ({len(story.pages)} pages)')

    print("Step 2/4 — Illustrating & narrating (parallel)...")
    with ThreadPoolExecutor(max_workers=2) as pool:
        illust_future = pool.submit(illustrator.run, story)
        narr_future = pool.submit(reader.run, story)

        illustrations = illust_future.result()
        narration = narr_future.result()

    print(f"  ✓ {len(illustrations.pages)} illustrations + audio ready")

    print("Step 3/4 — Building PDF & uploading...")
    publication: publisher.Publication = publisher.run(story, illustrations, narration)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  Book : {publication.book_url}")
    print(f"  Audio: {publication.audio_url}")

    return publication


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)

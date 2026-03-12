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


def configure_models() -> bool:
    """Returns True if narration is enabled."""
    choice = input("Model tier — (1) flash  (2) pro: ").strip()
    tier = "pro" if choice == "2" else "flash"
    for key, value in MODELS[tier].items():
        os.environ[key] = value
    print(f"  → models set to {tier}")

    narrate = input("Include narration? (y/n) [y]: ").strip().lower()
    narrate_on = narrate != "n"
    print(f"  → narration {'on' if narrate_on else 'off'}")
    return narrate_on


def main():
    narrate = configure_models()
    story_prompt = input("Story prompt (or Enter to skip): ").strip() or None
    t0 = time.time()

    total_steps = 4 if narrate else 3
    step = 0

    step += 1
    print(f"Step {step}/{total_steps} — Writing the story...")
    story: author.Story = author.run(story_prompt)
    print(f'  ✓ "{story.title}" ({len(story.pages)} pages)')

    step += 1
    narration = None
    if narrate:
        print(f"Step {step}/{total_steps} — Illustrating & narrating (parallel)...")
        with ThreadPoolExecutor(max_workers=2) as pool:
            illust_future = pool.submit(illustrator.run, story)
            narr_future = pool.submit(reader.run, story)
            illustrations = illust_future.result()
            narration = narr_future.result()
        print(f"  ✓ {len(illustrations.pages)} illustrations + audio ready")
    else:
        print(f"Step {step}/{total_steps} — Illustrating...")
        illustrations = illustrator.run(story)
        print(f"  ✓ {len(illustrations.pages)} illustrations ready")

    step += 1
    print(f"Step {step}/{total_steps} — Building PDF & uploading...")
    publication: publisher.Publication = publisher.run(story, illustrations, narration)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  Book : {publication.book_url}")
    if publication.audio_url:
        print(f"  Audio: {publication.audio_url}")

    return publication


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)

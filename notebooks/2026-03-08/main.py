import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents import author, illustrator, reader, publisher


def main():
    t0 = time.time()

    print("Step 1/4 — Writing the story...")
    story: author.Story = author.run()
    print(f"  ✓ \"{story.title}\" ({len(story.pages)} pages)")

    print("Step 2/4 — Illustrating & narrating (parallel)...")
    with ThreadPoolExecutor(max_workers=2) as pool:
        illust_future = pool.submit(illustrator.run, story)
        narr_future = pool.submit(reader.run, story)

        illustrations = illust_future.result()
        narration = narr_future.result()

    print(f"  ✓ {len(illustrations.pages)} illustrations + audio ready")

    print("Step 3/4 — Building PDF & uploading...")
    publication: publisher.Publication = publisher.run(
        story, illustrations, narration
    )

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

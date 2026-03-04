"""Demo for ImageParser."""

import base64
import copy

from pathlib import Path

from examples.mem_reader.samples import IMAGE_MESSAGE_CASES
from oh_memos.mem_reader.read_multi_modal.image_parser import ImageParser

from ._base import BaseParserDemo


class ImageParserDemo(BaseParserDemo):
    def create_parser(self):
        return ImageParser(embedder=self.embedder, llm=self.llm)

    def run(self):
        print("🚀 Initializing ImageParserDemo...")
        print("�?Initialization complete.")
        print("=== ImageParser Demo ===\n")

        info = {"user_id": "user1", "session_id": "session1"}

        test_cases = copy.deepcopy(IMAGE_MESSAGE_CASES)

        # Add Local Image (Base64) if exists
        local_img_path = Path(__file__).parent.parent / "test_image.png"
        if local_img_path.exists():
            with open(local_img_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
            test_cases.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_data}",
                        "detail": "auto",
                    },
                    "_note": "Local Image (Base64)",
                }
            )

        for i, msg in enumerate(test_cases, 1):
            print(f"--- Case {i}: Image URL message ---")

            # 1. Create SourceMessage
            print(f"📝 Creating SourceMessage from: {msg}")
            source = self.parser.create_source(msg, info)
            print("  �?Created SourceMessage:")
            print(f"     - Type: {source.type}")
            print(f"     - URL: {getattr(source, 'url', 'N/A')}")

            # 2. Rebuild from Source
            print("🔄 Rebuilding message from source...")
            rebuilt = self.parser.rebuild_from_source(source)
            print(f"  �?Rebuilt result: {rebuilt}")

            # 3. Fast Parse (Expected Empty)
            print("⚡️ Running parse_fast (expecting empty)...")
            fast_results = self.parser.parse_fast(msg, info)
            if not fast_results:
                print("  �?Got empty list as expected (images require fine mode).")
            else:
                print(f"  ⚠️  Unexpected fast results: {len(fast_results)} items")

            # 4. Fine Parse (Vision Model)
            print("🧠 Running parse_fine (Vision Model)...")
            # Note: This might fail if the configured LLM doesn't support vision or if the URL is unreachable
            try:
                fine_results = self.parser.parse_fine(msg, info)
                if not fine_results:
                    print(
                        "  ⚠️  No memories generated (LLM might not support vision or image inaccessible)."
                    )
                else:
                    print(f"  📊 Generated {len(fine_results)} memory item(s):")
                    for item in fine_results:
                        print(f"     - Memory: {item.memory[:100]}...")
            except Exception as e:
                print(f"  �?Error during fine parsing: {e}")

            print()


if __name__ == "__main__":
    demo = ImageParserDemo()
    demo.run()

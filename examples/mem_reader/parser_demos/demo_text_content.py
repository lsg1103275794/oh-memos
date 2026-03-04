"""Demo for TextContentParser."""

from examples.mem_reader.samples import TEXT_CONTENT_PARTS
from oh_memos.mem_reader.read_multi_modal.text_content_parser import TextContentParser

from ._base import BaseParserDemo


class TextContentParserDemo(BaseParserDemo):
    def create_parser(self):
        return TextContentParser(embedder=self.embedder, llm=self.llm)

    def run(self):
        print("=== TextContentParser Demo ===")

        info = {"user_id": "user1", "session_id": "session1"}

        for i, part in enumerate(TEXT_CONTENT_PARTS, 1):
            print(f"\n--- Part {i} ---")
            source = self.demo_source_creation(part, info)

            # Legacy example attempts to rebuild and access dict keys directly.
            # Since current source returns None, we must handle it safely in the demo.
            print("\n🔄 Rebuilding from source...")
            rebuilt = self.parser.rebuild_from_source(source)
            if rebuilt:
                print("  �?Rebuilt result:")
                if isinstance(rebuilt, dict):
                    from examples.mem_reader.utils import pretty_print_dict

                    pretty_print_dict(rebuilt)
                else:
                    print(f"     {rebuilt}")
            else:
                print("  ⚠️  Rebuilt result is None (not implemented in source)")


if __name__ == "__main__":
    demo = TextContentParserDemo()
    demo.run()

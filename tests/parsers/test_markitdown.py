import unittest

from memos.configs.parser import MarkItDownParserConfig
from memos.parsers.factory import MarkItDownParser


class TestMarkItDownParser(unittest.TestCase):
    def test_parse_docx_file(self):
        """Test parse a docx file."""
        config = MarkItDownParserConfig()
        parser = MarkItDownParser(config)
        file_path = "./README.md"
        content = parser.parse(file_path)

        self.assertIn("MemOS", content)

    def test_parse_pdf_file(self):
        """Test parse a pdf file."""
        config = MarkItDownParserConfig()
        parser = MarkItDownParser(config)
        file_path = "./examples/data/one_page_example.pdf"
        content = parser.parse(file_path)

        self.assertIn("Stray Birds", content)

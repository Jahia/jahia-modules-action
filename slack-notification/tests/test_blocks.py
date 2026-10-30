"""The blocks of a message: a text escapes what Slack reads as markup, the primary button stands out, and rich
text contains lines of words and links, and blocks of code."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from blocks import build_buttons, build_code, build_line, build_link, build_rich_text, build_word, escape


class TestTheBlocks(unittest.TestCase):
    def test_a_text_escapes_what_slack_reads_as_markup(self):
        self.assertEqual(escape("<&>"), "&lt;&amp;&gt;")

    def test_the_primary_button_stands_out(self):
        row = build_buttons(("View logs", "https://l"), ("View run", "https://r"), primary="View logs")
        self.assertEqual([button.get("style") for button in row["elements"]], ["primary", None])
        self.assertEqual([button["url"] for button in row["elements"]], ["https://l", "https://r"])

    def test_rich_text_contains_a_line_of_a_link_and_a_bold_word_then_a_block_of_code(self):
        block = build_rich_text(
            build_line(build_link("https://j", "job"), build_word("step", bold=True)), build_code("x")
        )
        self.assertEqual(
            block,
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {"type": "link", "url": "https://j", "text": "job"},
                            {"type": "text", "text": "step", "style": {"bold": True}},
                        ],
                    },
                    {"type": "rich_text_preformatted", "elements": [{"type": "text", "text": "x"}]},
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()

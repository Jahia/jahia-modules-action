"""The blocks of a message: a code block escapes its text and cannot be closed from inside, and the primary
button stands out."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from blocks import build_buttons, build_code, escape


class TestTheBlocks(unittest.TestCase):
    def test_a_code_block_escapes_its_text_and_cannot_be_closed_from_inside(self):
        block = build_code("a <b> & ```c```")
        self.assertEqual(block["text"]["text"], "```a &lt;b&gt; &amp; '''c'''```")
        self.assertEqual(escape("<&>"), "&lt;&amp;&gt;")

    def test_the_primary_button_stands_out(self):
        row = build_buttons(("View logs", "https://l"), ("View run", "https://r"), primary="View logs")
        self.assertEqual([button.get("style") for button in row["elements"]], ["primary", None])
        self.assertEqual([button["url"] for button in row["elements"]], ["https://l", "https://r"])


if __name__ == "__main__":
    unittest.main()

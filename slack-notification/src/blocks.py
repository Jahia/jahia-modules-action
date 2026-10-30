"""The Block Kit blocks of a Slack message, which every template of an event builds its message from. A block
of markdown escapes what Slack reads as markup, and a block of rich text needs no escape: `build_rich_text`
contains lines of words and links, and blocks of code."""


def escape(text: str) -> str:
    # Slack reads `&`, `<` and `>` as markup
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_header(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}


def build_section(markdown: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": markdown}}


def build_context(markdown: str) -> dict:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": markdown}]}


def build_divider() -> dict:
    return {"type": "divider"}


def build_buttons(*links: tuple[str, str], primary: str = "") -> dict:
    # Each link is a label and a URL, and the button whose label is `primary` stands out
    elements = []
    for label, url in links:
        button = {"type": "button", "text": {"type": "plain_text", "text": label}, "url": url}
        elements.append(button | {"style": "primary"} if label == primary else button)
    return {"type": "actions", "elements": elements}


def build_rich_text(*elements: dict) -> dict:
    return {"type": "rich_text", "elements": list(elements)}


def build_line(*elements: dict) -> dict:
    return {"type": "rich_text_section", "elements": list(elements)}


def build_code(text: str) -> dict:
    return {"type": "rich_text_preformatted", "elements": [build_word(text)]}


def build_word(text: str, **style: bool) -> dict:
    # A style is bold, italic, strike or code
    return {"type": "text", "text": text, **({"style": style} if style else {})}


def build_link(url: str, text: str, **style: bool) -> dict:
    return {"type": "link", "url": url, "text": text, **({"style": style} if style else {})}

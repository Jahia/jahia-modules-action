"""The Block Kit blocks of a Slack message, which every template of an event builds its message from. A
text that a block shows escapes what Slack reads as markup."""


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


def build_code(text: str) -> dict:
    # Slack has no longer fence, so a fence inside the text would close the block
    return build_section("```" + escape(text).replace("```", "'''") + "```")


def build_buttons(*links: tuple[str, str], primary: str = "") -> dict:
    # Each link is a label and a URL, and the button whose label is `primary` stands out
    elements = []
    for label, url in links:
        button = {"type": "button", "text": {"type": "plain_text", "text": label}, "url": url}
        elements.append(button | {"style": "primary"} if label == primary else button)
    return {"type": "actions", "elements": elements}

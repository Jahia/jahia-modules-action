"""The Web API of Slack, as the bot token of an app calls it, and the message the bot posts."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import NamedTuple

_API = "https://slack.com/api/"


class SlackMessage(NamedTuple):
    """A message on a bar in the color of its state. `fallback` is the text that the notification of the
    system shows, and `thread` lists the blocks of each reply in the thread of the message. `metadata` is
    `{"event_type": str, "event_payload": dict}`, which `find_message` matches later."""

    color: str
    fallback: str
    blocks: list[dict]
    thread: tuple[list[dict], ...] = ()
    metadata: dict | None = None

    def _render(self, channel: str) -> dict:
        # An attachment draws the bar, and a message with no text of its own shows no line above it
        payload = {
            "channel": channel,
            "attachments": [{"color": self.color, "fallback": self.fallback, "blocks": self.blocks}],
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


class SlackError(Exception):
    """A call that Slack refused, named by the error code that Slack returns, or by its HTTP status."""


class SlackClient:
    def __init__(self, token: str) -> None:
        self._token = token

    def find_member(self, email: str) -> str:
        """The ID of the member whose email is `email`, empty when Slack knows none."""
        try:
            return self._call("users.lookupByEmail", query={"email": email})["user"]["id"]
        except SlackError as fault:
            if str(fault) == "users_not_found":
                return ""
            raise

    def post(self, channel: str, message: SlackMessage) -> tuple[str, str]:
        """The `channel` and the `ts` of the message. Each reply of the thread follows it, under its timestamp."""
        result = self._call("chat.postMessage", message._render(channel))
        for blocks in message.thread:
            reply = {
                "channel": result["channel"],
                "thread_ts": result["ts"],
                "text": message.fallback,
                "blocks": blocks,
            }
            self._call("chat.postMessage", reply)
        return result["channel"], result["ts"]

    def update(self, channel: str, ts: str, message: SlackMessage) -> None:
        """Rewrite the message posted at `ts` with `message`."""
        self._call("chat.update", {**message._render(channel), "ts": ts})

    def find_message(self, member: str, metadata: dict) -> tuple[str, str, list[dict]] | None:
        """The `channel`, the `ts` and the blocks of the newest message of the member with `metadata`."""
        channel = self._call("conversations.open", {"users": member})["channel"]["id"]
        query = {"channel": channel, "include_all_metadata": "true", "limit": 100}
        for found in self._call("conversations.history", query=query)["messages"]:
            if found.get("metadata") == metadata:
                return channel, found["ts"], found["attachments"][0]["blocks"]
        return None

    def _call(self, method: str, payload: dict | None = None, query: dict | None = None) -> dict:
        url = _API + method + (f"?{urllib.parse.urlencode(query)}" if query else "")
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json; charset=utf-8"}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=30) as response:
                body = json.load(response)
        except urllib.error.HTTPError as fault:
            # Slack refuses a rate limit with an HTTP status, and no body that names an error
            raise SlackError(f"HTTP {fault.code}") from fault
        except (urllib.error.URLError, TimeoutError) as fault:
            raise SlackError(f"no response: {getattr(fault, 'reason', fault)}") from fault
        if not body.get("ok"):
            raise SlackError(body.get("error", "no error code"))
        return body

"""The client of a Slack app: a member Slack does not know is no error, any other refusal raises, and a post
sends the replies of its thread under the message. A message draws its bar and keeps its text for the system,
and its blocks escape what Slack reads as markup."""

import io
import json
import pathlib
import sys
import unittest
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from slack import SlackClient, SlackError, SlackMessage, _build_buttons, _build_code, _escape


class TestTheClient(unittest.TestCase):
    def serve(self, *bodies):
        """Slack returns the next of `bodies` for each call, and the test keeps the requests."""
        self.requests = []

        def urlopen(request, timeout):
            self.requests.append(request)
            return io.BytesIO(json.dumps(bodies[len(self.requests) - 1]).encode())

        self.enterContext(mock.patch.object(urllib.request, "urlopen", urlopen))

    def test_a_member_comes_from_its_email_and_an_unknown_email_gives_no_member(self):
        self.serve({"ok": True, "user": {"id": "U1"}}, {"ok": False, "error": "users_not_found"})
        client = SlackClient("xoxb-test")
        self.assertEqual(client.find_member("a@j.com"), "U1")
        self.assertEqual(client.find_member("b@j.com"), "")
        self.assertEqual(self.requests[0].full_url, "https://slack.com/api/users.lookupByEmail?email=a%40j.com")
        self.assertEqual(self.requests[0].get_header("Authorization"), "Bearer xoxb-test")

    def test_another_refusal_raises_with_the_error_code_of_slack(self):
        self.serve({"ok": False, "error": "missing_scope"})
        with self.assertRaisesRegex(SlackError, "missing_scope"):
            SlackClient("t").find_member("a@j.com")

    def test_a_post_sends_each_reply_of_the_thread_under_the_message(self):
        self.serve({"ok": True, "channel": "D1", "ts": "1.5"}, {"ok": True})
        SlackClient("t").post("U1", SlackMessage("#fff", "text", [], ([{"type": "divider"}],)))
        payloads = [json.loads(request.data) for request in self.requests]
        self.assertEqual(payloads[0]["channel"], "U1")
        self.assertEqual(
            payloads[1], {"channel": "D1", "thread_ts": "1.5", "text": "text", "blocks": [{"type": "divider"}]}
        )

    def test_an_http_status_such_as_a_rate_limit_raises_with_the_status(self):
        def urlopen(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", None, None)

        self.enterContext(mock.patch.object(urllib.request, "urlopen", urlopen))
        with self.assertRaisesRegex(SlackError, "HTTP 429"):
            SlackClient("t").find_member("a@j.com")


class TestTheMessage(unittest.TestCase):
    def test_a_message_sits_on_a_bar_with_its_fallback_and_no_text_of_its_own(self):
        payload = SlackMessage("#E01E5A", "❌ failed", [{"type": "divider"}]).render("U1")
        self.assertEqual(
            payload,
            {
                "channel": "U1",
                "attachments": [{"color": "#E01E5A", "fallback": "❌ failed", "blocks": [{"type": "divider"}]}],
            },
        )

    def test_a_code_block_escapes_its_text_and_cannot_be_closed_from_inside(self):
        self.assertEqual(_build_code("a <b> & ```c```")["text"]["text"], "```a &lt;b&gt; &amp; '''c'''```")
        self.assertEqual(_escape("<&>"), "&lt;&amp;&gt;")

    def test_the_primary_button_stands_out(self):
        row = _build_buttons(("View logs", "https://l"), ("View run", "https://r"), primary="View logs")
        self.assertEqual([button.get("style") for button in row["elements"]], ["primary", None])
        self.assertEqual([button["url"] for button in row["elements"]], ["https://l", "https://r"])


if __name__ == "__main__":
    unittest.main()

"""The client of a Slack app: a member Slack does not know is no error, any other refusal raises, and a post
sends the replies of its thread under the message. A message draws its bar and keeps its text for the system."""

import io
import json
import pathlib
import sys
import unittest
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from slack import SlackClient, SlackError, SlackMessage


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

    def test_a_post_returns_the_channel_and_the_ts_and_sends_the_metadata(self):
        self.serve({"ok": True, "channel": "D1", "ts": "1.5"})
        metadata = {"event_type": "review_requested", "event_payload": {"number": 42}}
        self.assertEqual(SlackClient("t").post("U1", SlackMessage("#fff", "t", [], (), metadata)), ("D1", "1.5"))
        self.assertEqual(json.loads(self.requests[0].data)["metadata"], metadata)

    def test_an_update_rewrites_the_message_at_its_ts(self):
        self.serve({"ok": True})
        SlackClient("t").update("D1", "1.5", SlackMessage("#2EB67D", "t", [{"type": "divider"}]))
        payload = json.loads(self.requests[0].data)
        self.assertEqual(
            (self.requests[0].full_url.rsplit("/", 1)[1], payload["channel"], payload["ts"]),
            ("chat.update", "D1", "1.5"),
        )

    def test_the_newest_message_with_the_metadata_is_found_and_none_otherwise(self):
        wanted = {"event_type": "review_requested", "event_payload": {"number": 42}}
        history = [
            {"ts": "3", "metadata": {"event_type": "other", "event_payload": {}}},
            {"ts": "2", "metadata": wanted, "attachments": [{"blocks": [{"type": "header"}]}]},
        ]
        self.serve(
            {"ok": True, "channel": {"id": "D1"}},
            {"ok": True, "messages": history},
            {"ok": True, "channel": {"id": "D1"}},
            {"ok": True, "messages": []},
        )
        client = SlackClient("t")
        self.assertEqual(client.find_message("U1", wanted), ("D1", "2", [{"type": "header"}]))
        self.assertIsNone(client.find_message("U1", wanted))

    def test_an_http_status_such_as_a_rate_limit_raises_with_the_status(self):
        def urlopen(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", None, None)

        self.enterContext(mock.patch.object(urllib.request, "urlopen", urlopen))
        with self.assertRaisesRegex(SlackError, "HTTP 429"):
            SlackClient("t").find_member("a@j.com")

    def test_a_network_fault_raises_with_its_reason(self):
        def urlopen(request, timeout):
            raise urllib.error.URLError("timed out")

        self.enterContext(mock.patch.object(urllib.request, "urlopen", urlopen))
        with self.assertRaisesRegex(SlackError, "no response: timed out"):
            SlackClient("t").find_member("a@j.com")


class TestTheMessage(unittest.TestCase):
    def test_a_message_sits_on_a_bar_with_its_fallback_and_no_text_of_its_own(self):
        payload = SlackMessage("#E01E5A", "❌ failed", [{"type": "divider"}])._render("U1")
        self.assertEqual(
            payload,
            {
                "channel": "U1",
                "attachments": [{"color": "#E01E5A", "fallback": "❌ failed", "blocks": [{"type": "divider"}]}],
            },
        )


if __name__ == "__main__":
    unittest.main()

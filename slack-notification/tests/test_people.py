"""The email of a GitHub account comes from the last commit of the pull request that GitHub links to it."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import people
from fakes import FakeGitHub


class TestTheEmailOfThePerson(unittest.TestCase):
    def test_the_last_commit_linked_to_the_login_as_author_or_committer_gives_the_email(self):
        commits = [
            {"author": {"login": "a"}, "committer": {"login": "a"}, "commit": {"author": {"email": "a1@j.com"}}},
            {"author": None, "committer": {"login": "a"}, "commit": {"committer": {"email": "a2@j.com"}}},
            {"author": {"login": "b"}, "committer": {"login": "b"}, "commit": {"author": {"email": "b@j.com"}}},
        ]
        github = FakeGitHub({("list_pull_commits", 42): commits})
        self.assertEqual(people.find_email(github, "a", 42), "a2@j.com")
        self.assertEqual(people.find_email(github, "b", 42), "b@j.com")
        self.assertEqual(people.find_email(github, "c", 42), "")


if __name__ == "__main__":
    unittest.main()

"""The emails of a GitHub account come from the commits of the pull request that GitHub links to it."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import people
from fakes import FakeGitHub


def build_commit(author, author_email, committer="web-flow", committer_email="noreply@github.com"):
    """A commit of a pull request, as the REST API of GitHub returns it."""
    return {
        "author": {"login": author} if author else None,
        "committer": {"login": committer},
        "commit": {"author": {"email": author_email}, "committer": {"email": committer_email}},
    }


class TestTheEmailsOfThePerson(unittest.TestCase):
    def test_the_commits_linked_to_the_login_give_the_emails_the_last_first_without_the_noreply_address(self):
        commits = [
            build_commit("a", "a1@j.com"),
            build_commit("a", "1+a@users.noreply.github.com"),
            build_commit(None, "x@j.com", "a", "a2@j.com"),
            build_commit("b", "b@j.com"),
        ]
        github = FakeGitHub({("list_pull_commits", 42): commits})
        self.assertEqual(people.find_emails(github, "a", 42), ["a2@j.com", "a1@j.com"])
        self.assertEqual(people.find_emails(github, "b", 42), ["b@j.com"])
        self.assertEqual(people.find_emails(github, "c", 42), [])


if __name__ == "__main__":
    unittest.main()

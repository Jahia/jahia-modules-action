---
# Allowed version bumps: patch, minor, major
jahia-modules-action: patch
---

Fixed the AI PR review failing at `Prepare the review prompt and the log directory` with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xfc` on any pull request whose diff carries a non-UTF-8 file — a latin-1 encoded `.properties` translation is enough. The pre-fetch decoded every command's output as strict UTF-8, and the error was raised inside `subprocess.run` itself, so it escaped the handler that makes each fetch best-effort and killed the whole step before the agent ever started. Output is now decoded with `errors='replace'`, so an unreadable byte costs that one character instead of the review.

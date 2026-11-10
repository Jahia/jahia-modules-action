#!/usr/bin/env python3
"""A stand-in for gh: it answers each call from the first rule of the scenario that matches, and logs
the call. A rule matches when its `args` text is in the arguments and its `stdin` text is in the input."""

import json
import os
import sys

args = " ".join(sys.argv[1:])
stdin = sys.stdin.read()
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"args": args, "stdin": stdin}) + "\n")
with open(os.environ["FAKE_GH_SCENARIO"], encoding="utf-8") as fh:
    rules = json.load(fh)
for rule in rules:
    if rule["args"] in args and rule.get("stdin", "") in stdin:
        sys.stdout.write(rule.get("out", ""))
        sys.stderr.write(rule.get("err", ""))
        sys.exit(rule.get("exit", 0))
sys.stderr.write(f"unexpected call: gh {args}\n")
sys.exit(1)

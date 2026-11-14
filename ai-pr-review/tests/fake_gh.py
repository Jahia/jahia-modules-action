#!/usr/bin/env python3
"""A stand-in for gh: it answers each call from the first rule of the scenario that matches, and logs
the call. A rule matches when its `args` text is in the arguments and its `stdin` text is in the input,
from the call number `from_call` of the calls that it matches, the first one by default."""

import json
import os
import sys

args = " ".join(sys.argv[1:])
stdin = sys.stdin.read()
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"args": args, "stdin": stdin}) + "\n")
with open(os.environ["FAKE_GH_LOG"], encoding="utf-8") as log:
    calls = [json.loads(line) for line in log]
with open(os.environ["FAKE_GH_SCENARIO"], encoding="utf-8") as fh:
    rules = json.load(fh)


def matches(rule, call):
    return rule["args"] in call["args"] and rule.get("stdin", "") in call["stdin"]


for rule in rules:
    if matches(rule, calls[-1]) and sum(matches(rule, call) for call in calls) >= rule.get("from_call", 1):
        sys.stdout.write(rule.get("out", ""))
        sys.stderr.write(rule.get("err", ""))
        sys.exit(rule.get("exit", 0))
sys.stderr.write(f"unexpected call: gh {args}\n")
sys.exit(1)

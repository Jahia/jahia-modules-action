"""Run a script of the action against the fake gh, in a temporary directory."""

import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"


class FakeGh:
    def __init__(self, test, rules):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        test.addCleanup(shutil.rmtree, self.dir)
        bin_dir = self.dir / "bin"
        bin_dir.mkdir()
        # git answers from the same scenario, so a checkout runs with no clone.
        for name in ("gh", "git"):
            program = bin_dir / name
            shutil.copy(pathlib.Path(__file__).with_name("fake_gh.py"), program)
            program.chmod(program.stat().st_mode | stat.S_IEXEC)
        self.scenario = self.dir / "scenario.json"
        self.scenario.write_text(json.dumps(rules), encoding="utf-8")
        self.log = self.dir / "calls.log"
        self.log.touch()
        self.path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"

    def run(self, script, *args, env=None):
        environ = {**os.environ, "PATH": self.path, "FAKE_GH_SCENARIO": str(self.scenario),
                   "FAKE_GH_LOG": str(self.log), **(env or {})}
        return subprocess.run([sys.executable, str(SRC / script), *args], env=environ,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)

    def calls(self, text=""):
        calls = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        return [call for call in calls if text in call["args"]]

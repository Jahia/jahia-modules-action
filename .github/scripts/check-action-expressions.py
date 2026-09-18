"""Reject ${{ }} template expressions whose root named-value is not an Actions context.

Two gaps make this worth its own check:

- `actionlint` validates workflow files under .github/workflows/ only. The composite
  `action.yml` manifests that make up most of this repository are never checked by it,
  and a bad expression in one of them fails at `Set up job` in every consumer.
- GitHub expands template expressions inside `run:` bodies *before* the shell runs, so a
  `#` comment is no protection: an expression written there as an illustration is still
  evaluated, and an unknown name makes the whole action fail to load.

Both of those shipped in v2.73.0/v2.73.1 and broke every repository pinned to @v2.

Usage: python3 .github/scripts/check-action-expressions.py [path…]  (default: repository root)
Exits 1 when something is wrong, printing `file:line: …` for each finding.
"""
import pathlib
import re
import sys

# Context names and expression functions GitHub resolves. Anything else at the root of an
# expression is what the runner reports as "Unrecognized named-value".
VALID_ROOTS = {
    'github', 'env', 'vars', 'job', 'jobs', 'steps', 'runner', 'secrets', 'strategy',
    'matrix', 'needs', 'inputs', 'always', 'success', 'failure', 'cancelled', 'hashFiles',
    'format', 'join', 'toJSON', 'toJson', 'fromJSON', 'fromJson', 'contains', 'startsWith',
    'endsWith', 'true', 'false', 'null',
}

EXPRESSION = re.compile(r'\$\{\{(.+?)\}\}', re.S)
# Expression string literals are single-quoted ('' escapes a quote); their content is data.
STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")
# A root named-value: an identifier not preceded by '.' or '-', which continue a property path
# (property names may contain hyphens, e.g. inputs.retention-days).
ROOT_NAME = re.compile(r'(?<![.\-\w])([A-Za-z_][A-Za-z0-9_-]*)')


def files_to_check(roots):
    for root in roots:
        base = pathlib.Path(root)
        candidates = list(base.rglob('action.yml')) + list(base.rglob('action.yaml'))
        candidates += list((base / '.github' / 'workflows').glob('*.yml'))
        candidates += list((base / '.github' / 'workflows').glob('*.yaml'))
        for path in candidates:
            if 'node_modules' not in path.parts:
                yield path


def main():
    roots = sys.argv[1:] or ['.']
    findings = 0
    checked = 0
    for path in sorted(set(files_to_check(roots))):
        checked += 1
        text = path.read_text(encoding='utf-8', errors='replace')
        for match in EXPRESSION.finditer(text):
            expression = STRING_LITERAL.sub("''", match.group(1))
            line = text[:match.start()].count('\n') + 1
            for name in ROOT_NAME.findall(expression):
                if name not in VALID_ROOTS:
                    print(f'{path}:{line}: unrecognized named-value {name!r} in '
                          f'${{{{{match.group(1).strip()}}}}}')
                    findings += 1
    print(f'Checked {checked} action manifests and workflows, {findings} problem(s) found.')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())

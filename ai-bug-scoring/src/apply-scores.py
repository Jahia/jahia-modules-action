"""Score each selected bug from its factors file, then write the PM Score field and the comment.

Usage: apply-scores.py <log-dir>
Env:   WRITE          - "true": write the field and post the comments; anything else: review
                        mode, which writes nothing to GitHub and stores the would-be comments
                        under <log-dir>/comments/
       MARKER         - hidden marker that opens the score comment
       AGENT, RUN_URL - the footer of the comment
       DATE           - the date of the comment (YYYY-MM-DD)
       GH_TOKEN       - token that reads and posts the comments (read by gh)
       FIELD_TOKEN    - token that writes the PM Score issue field

A bug with no valid factors gets nothing, so its field stays empty and the next run tries it
again. A security bug gets the field value -1 and no comment: a comment on a public repository
would disclose it. The comment goes before the field, so a failed field write leaves the bug
eligible, and the next run edits the same comment instead of posting a second one.
Writes <log-dir>/results.json and one row per bug to the job summary. Exits 0 unless a script
error occurs: a skipped bug is a warning.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scoring  # noqa: E402

def gh(args, token, payload=None):
    """Run gh api with one token; a JSON payload goes through a file, never through argv."""
    env = dict(os.environ, GH_TOKEN=token)
    if payload is None:
        return subprocess.run(['gh', 'api', *args], env=env, check=True, capture_output=True, text=True).stdout
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as fh:
        json.dump(payload, fh)
    try:
        return subprocess.run(['gh', 'api', *args, '--input', fh.name], env=env, check=True,
                              capture_output=True, text=True).stdout
    finally:
        os.unlink(fh.name)


def set_field(bug, value, token):
    gh(['--method', 'POST', f'repos/{bug["repository"]}/issues/{bug["number"]}/issue-field-values'],
       token, {'issue_field_values': [{'field_id': bug['field_id'], 'value': value}]})


def upsert_comment(bug, body, marker, token):
    """Edit the score comment of the bug when there is one, or post a new one."""
    base = f'repos/{bug["repository"]}/issues'
    pages = gh(['--paginate', '--slurp', f'{base}/{bug["number"]}/comments?per_page=100'], token)
    comments = [c for page in json.loads(pages) for c in page]
    mine = [c for c in comments if (c.get('body') or '').startswith(marker)]
    if mine:
        gh(['--method', 'PATCH', f'{base}/comments/{mine[-1]["id"]}'], token, {'body': body})
        return 'edited'
    gh(['--method', 'POST', f'{base}/{bug["number"]}/comments'], token, {'body': body})
    return 'posted'


def load(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as error:
        return error


def evaluate(bug, log_dir, env):
    """Return the result of one bug: its value, its comment, or the reason it is skipped."""
    ref = f'{bug["repository"]}#{bug["number"]}'
    result = {'ref': ref, 'key': bug['key'], 'url': bug['url']}
    ticket = load(os.path.join(log_dir, 'tickets', f'{bug["key"]}.json'))
    factors = load(os.path.join(log_dir, 'factors', f'{bug["key"]}.json'))
    if isinstance(ticket, Exception):
        return dict(result, outcome='skipped', reason='ticket not fetched')
    if isinstance(factors, Exception):
        return dict(result, outcome='skipped', reason=f'no factors ({factors.__class__.__name__})')
    problems = scoring.check(factors, ref)
    if problems:
        return dict(result, outcome='skipped', reason='invalid factors: ' + '; '.join(problems))
    if factors['security']:
        return dict(result, outcome='security', value=scoring.SECURITY_VALUE)
    points, rows, p1 = scoring.score(factors, ticket['labels'])
    comment = scoring.render_comment(env['MARKER'], points, rows, p1, factors,
                                     env.get('AGENT', 'Claude Code'), env.get('RUN_URL', ''), env.get('DATE', ''))
    return dict(result, outcome='scored', value=scoring.field_value(points, p1), points=points, p1=p1,
                impact=factors['impact'], reach=factors['reach'], customers=factors['customers'],
                confidence=factors['confidence'], comment=comment)


def write(bug, result, env):
    """Send the writes of one bug: the comment of a scored bug, then its PM Score field."""
    if result['outcome'] == 'scored':
        result['comment_action'] = upsert_comment(bug, result['comment'], env['MARKER'], env['GH_TOKEN'])
    set_field(bug, result['value'], env['FIELD_TOKEN'])
    result['written'] = True


def summary_row(result):
    value = result.get('value', '')
    p1 = 'P1' if result.get('p1') else ''
    detail = result.get('reason') or ' / '.join(str(result[k]) for k in ('impact', 'reach') if k in result)
    outcome = result['outcome'] + (', written' if result.get('written') else '')
    return f'| [{result["ref"]}]({result["url"]}) | {value} | {p1} | {detail} | {outcome} |'


def main():
    log_dir = sys.argv[1]
    env = os.environ
    writing = env.get('WRITE') == 'true'
    with open(os.path.join(log_dir, 'selected-bugs.json'), encoding='utf-8') as fh:
        bugs = json.load(fh)
    comments_dir = os.path.join(log_dir, 'comments')
    os.makedirs(comments_dir, exist_ok=True)

    results = []
    for bug in bugs:
        result = evaluate(bug, log_dir, env)
        if result['outcome'] == 'skipped':
            print(f'::warning::{result["ref"]}: {result["reason"]}. Its field stays empty, so the next run tries it again')
        elif writing:
            try:
                write(bug, result, env)
            except subprocess.CalledProcessError as error:
                result['outcome'] = 'write failed'
                result['reason'] = (error.stderr or '').strip()[:200]
                print(f'::warning::{result["ref"]}: a write failed ({result["reason"]}). The next run tries it again')
        elif result['outcome'] == 'scored':
            with open(os.path.join(comments_dir, f'{bug["key"]}.comment.md'), 'w', encoding='utf-8') as fh:
                fh.write(result['comment'])
        print(f'{result["ref"]}: {result["outcome"]} {result.get("value", "")}')
        results.append(result)

    with open(os.path.join(log_dir, 'results.json'), 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)
    summary = env.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write(f'### PM scores ({"written" if writing else "review mode, nothing written"})\n\n')
            fh.write('| Bug | Field value | | Impact / reach, or reason | Outcome |\n')
            fh.write('|---|---|---|---|---|\n')
            fh.write(''.join(summary_row(r) + '\n' for r in results))


if __name__ == '__main__':
    main()

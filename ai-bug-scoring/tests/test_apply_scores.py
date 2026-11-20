"""apply-scores.py: what a dry run stores, and what write mode sends, in which order."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
MARKER = '<!-- ai-bug-scoring -->'
FIELD_ID = 50177867

FAKE_GH = textwrap.dedent('''\
    #!{python}
    """Record each call, and answer the list of comments with one earlier score comment."""
    import json, os, sys
    args = sys.argv[2:]  # after "api"
    payload = None
    if '--input' in args:
        with open(args[args.index('--input') + 1], encoding='utf-8') as fh:
            payload = json.load(fh)
    with open(os.environ['FAKE_GH_LOG'], 'a', encoding='utf-8') as fh:
        fh.write(json.dumps({{'args': args, 'payload': payload, 'credential': os.environ.get('GH_TOKEN')}}) + '\\n')
    if '--paginate' in args:
        print(json.dumps([[{{'id': 7, 'body': os.environ['MARKER'] + '\\nold score'}}]]))
    else:
        print('{{}}')
''')


def bug(number):
    return {'key': f'Jahia-example-{number}', 'repository': 'Jahia/example', 'number': number,
            'url': f'https://github.com/Jahia/example/issues/{number}', 'field_id': FIELD_ID}


def factors(number, **over):
    base = {'ref': f'Jahia/example#{number}', 'security': False, 'impact': 'editorBlocked',
            'feature': 'jContent paste', 'reach': 'high', 'workaround': 'painful', 'regression': True,
            'clear': True, 'cloud': False, 'older_version_only': False, 'customers': 1,
            'confidence': 'high', 'why': 'Editors cannot paste.'}
    base.update(over)
    return base


class ApplyScoresTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        for sub in ('tickets', 'factors'):
            os.makedirs(os.path.join(self.dir, sub))
        # 1: scored; 2: a security bug; 3: the agent wrote no factors.
        self.bugs = [bug(1), bug(2), bug(3)]
        self.write_json('selected-bugs.json', self.bugs)
        for b in self.bugs:
            self.write_json(f'tickets/{b["key"]}.json', {'labels': ['customer']})
        self.write_json('factors/Jahia-example-1.json', factors(1))
        self.write_json('factors/Jahia-example-2.json', factors(2, security=True))

    def write_json(self, name, data):
        with open(os.path.join(self.dir, name), 'w', encoding='utf-8') as fh:
            json.dump(data, fh)

    def run_apply(self, dry_run):
        bin_dir = os.path.join(self.dir, 'bin')
        os.makedirs(bin_dir, exist_ok=True)
        fake = os.path.join(bin_dir, 'gh')
        with open(fake, 'w', encoding='utf-8') as fh:
            fh.write(FAKE_GH.format(python=sys.executable))
        os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.dir, 'gh.log')
        env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ['PATH'], FAKE_GH_LOG=self.log,
                   DRY_RUN='true' if dry_run else 'false', MARKER=MARKER, GH_TOKEN='comment-credential',
                   FIELD_TOKEN='field-credential', DATE='2026-11-20', RUN_URL='https://run')
        env.pop('GITHUB_STEP_SUMMARY', None)
        subprocess.run([sys.executable, os.path.join(SRC, 'apply-scores.py'), self.dir], env=env, check=True,
                       capture_output=True, text=True)
        with open(os.path.join(self.dir, 'results.json'), encoding='utf-8') as fh:
            return {r['ref']: r for r in json.load(fh)}

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding='utf-8') as fh:
            return [json.loads(line) for line in fh]

    def test_dry_run_stores_the_comment_and_sends_nothing(self):
        results = self.run_apply(dry_run=True)
        self.assertEqual(results['Jahia/example#1']['outcome'], 'scored')
        self.assertEqual(results['Jahia/example#1']['value'], 55)
        self.assertEqual(results['Jahia/example#2']['outcome'], 'security')
        self.assertEqual(results['Jahia/example#3']['outcome'], 'skipped')
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'comments', 'Jahia-example-1.comment.md')))
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'comments', 'Jahia-example-2.comment.md')))
        self.assertEqual(self.calls(), [])

    def test_write_mode_edits_the_comment_then_sets_the_field(self):
        results = self.run_apply(dry_run=False)
        self.assertTrue(results['Jahia/example#1']['written'])
        self.assertEqual(results['Jahia/example#1']['comment_action'], 'edited')
        # The bugs go in order, so the first three calls are those of bug 1.
        first = self.calls()[:3]
        self.assertIn('--paginate', first[0]['args'])
        self.assertIn('repos/Jahia/example/issues/1/comments?per_page=100', first[0]['args'])
        self.assertEqual(first[1]['args'][:3], ['--method', 'PATCH', 'repos/Jahia/example/issues/comments/7'])
        self.assertTrue(first[1]['payload']['body'].startswith(MARKER))
        self.assertEqual(first[1]['credential'], 'comment-credential')
        self.assertEqual(first[2]['args'][:3],
                         ['--method', 'POST', 'repos/Jahia/example/issues/1/issue-field-values'])
        self.assertEqual(first[2]['payload'], {'issue_field_values': [{'field_id': FIELD_ID, 'value': 55}]})
        self.assertEqual(first[2]['credential'], 'field-credential')

    def test_write_mode_gives_a_security_bug_minus_one_and_no_comment(self):
        self.run_apply(dry_run=False)
        security = [c for c in self.calls() if any('issues/2' in a for a in c['args'])]
        self.assertEqual(len(security), 1)
        self.assertEqual(security[0]['args'][:3],
                         ['--method', 'POST', 'repos/Jahia/example/issues/2/issue-field-values'])
        self.assertEqual(security[0]['payload'], {'issue_field_values': [{'field_id': FIELD_ID, 'value': -1}]})

    def test_write_mode_sends_nothing_for_a_bug_with_no_factors(self):
        results = self.run_apply(dry_run=False)
        self.assertNotIn('written', results['Jahia/example#3'])
        self.assertFalse([c for c in self.calls() if any('issues/3' in a for a in c['args'])])


if __name__ == '__main__':
    unittest.main()

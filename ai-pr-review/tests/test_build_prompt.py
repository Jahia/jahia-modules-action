"""The allow list and the tool surface that src/build-prompt.py writes for one run."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'src', 'build-prompt.py')
PR_URL = 'https://github.com/Jahia/example/pull/7'
REVIEW_NAME = 'pr-Jahia-example-7.review.json'


def run_build_prompt(log_dir, allowed_tools, disallowed_tools='', review_round='', cortex_path=None):
    """Run the script as the prep step does, and return the allow list and the surface it writes."""
    if cortex_path is None:
        cortex_path = os.path.join(os.path.dirname(log_dir), 'cortex')
    env = dict(os.environ, PR_URL=PR_URL, MARKER='<!-- marker -->', CORTEX_PATH=cortex_path,
               ALLOWED_TOOLS=allowed_tools, DISALLOWED_TOOLS=disallowed_tools, REVIEW_ROUND=review_round)
    subprocess.run([sys.executable, SCRIPT, log_dir], env=env, check=True,
                   capture_output=True, text=True)
    with open(os.path.join(log_dir, 'allowed-tools.txt'), encoding='utf-8') as fh:
        allowed = fh.read().rstrip('\n')
    with open(os.path.join(log_dir, 'review.system.md'), encoding='utf-8') as fh:
        surface = fh.read()
    return allowed, surface


class BuildPromptTest(unittest.TestCase):

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def test_the_allow_list_ends_on_the_three_rules_of_the_run(self):
        log_dir = os.path.join(self.root, 'logs')
        allowed, _ = run_build_prompt(log_dir, 'Read,Bash(git log:*)')
        self.assertEqual(allowed, ','.join([
            'Read,Bash(git log:*)',
            f'Edit(/{log_dir}/reviews/**)',
            f'Edit(/{log_dir}/collected/**)',
            f'Bash(python3 -m json.tool {log_dir}/reviews/{REVIEW_NAME})',
        ]))

    def read_denied(self, log_dir):
        with open(os.path.join(log_dir, 'disallowed-tools.txt'), encoding='utf-8') as fh:
            return fh.read().rstrip('\n')

    def test_the_deny_list_ends_on_the_rule_of_the_cortex_checkout(self):
        """An absolute rule: Claude Code 2.1.325 matches `Edit(./**)` in the --add-dir log directory too."""
        log_dir = os.path.join(self.root, 'logs')
        cortex = os.path.join(self.root, 'cortex')
        run_build_prompt(log_dir, 'Read', 'Edit,Bash(git push:*)', cortex_path=cortex)
        self.assertEqual(self.read_denied(log_dir), f'Edit,Bash(git push:*),Edit(/{cortex}/**)')

    def test_the_deny_rule_names_the_resolved_cortex_checkout(self):
        target = os.path.join(self.root, 'target')
        os.mkdir(target)
        link = os.path.join(self.root, 'link')
        os.symlink(target, link)
        log_dir = os.path.join(self.root, 'logs')
        run_build_prompt(log_dir, 'Read', cortex_path=link)
        self.assertEqual(self.read_denied(log_dir), f'Edit(/{target}/**)')

    def test_the_surface_names_the_deny_rule_of_the_cortex_checkout(self):
        cortex = os.path.join(self.root, 'cortex')
        _, surface = run_build_prompt(os.path.join(self.root, 'logs'), 'Read', 'Edit', cortex_path=cortex)
        self.assertIn(f'- Tools: Edit, Edit(/{cortex}/**).\n', surface)

    def test_a_log_directory_inside_the_cortex_checkout_stops_the_script(self):
        """The deny rule of the checkout would refuse every write of the agent."""
        cortex = os.path.join(self.root, 'cortex')
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            run_build_prompt(os.path.join(cortex, 'logs'), 'Read', cortex_path=cortex)
        self.assertIn('inside the cortex checkout', raised.exception.stderr)

    def test_the_default_deny_list_of_the_action_carries_no_relative_edit_rule(self):
        action = os.path.join(os.path.dirname(os.path.dirname(SCRIPT)), 'action.yml')
        with open(action, encoding='utf-8') as fh:
            default = re.search(r"\n  disallowed_tools:\n(?:    .*\n)*?    default: '([^']*)'", fh.read()).group(1)
        self.assertTrue(default.startswith('Edit,'))
        self.assertNotIn('Edit(./**)', default)

    def read_call(self, log_dir):
        with open(os.path.join(log_dir, 'review.prompt.md'), encoding='utf-8') as fh:
            return fh.read()

    def test_the_call_passes_the_round_that_the_trail_gives(self):
        """A runner keeps no trace between runs, so the prep step reads the round from the trail of the PR."""
        log_dir = os.path.join(self.root, 'logs')
        run_build_prompt(log_dir, 'Read', review_round='3')
        self.assertTrue(self.read_call(log_dir).rstrip('\n').endswith(' --round 3'))

    def test_the_call_with_no_round_passes_none(self):
        """With no checkout, or with a Cortex that has no trail, the run records no round."""
        log_dir = os.path.join(self.root, 'logs')
        run_build_prompt(log_dir, 'Read')
        self.assertNotIn('--round', self.read_call(log_dir))

    def test_the_rules_name_the_resolved_log_directory(self):
        """A rule that names a symbolic link may not match the path that the CLI compares."""
        target = os.path.join(self.root, 'target')
        os.mkdir(target)
        link = os.path.join(self.root, 'link')
        os.symlink(target, link)
        allowed, _ = run_build_prompt(link, 'Read')
        self.assertIn(f'Edit(/{target}/reviews/**)', allowed)
        self.assertNotIn(link, allowed)

    def test_a_prefix_entry_ends_on_the_marker_in_the_surface(self):
        _, surface = run_build_prompt(os.path.join(self.root, 'logs'),
                                      'Bash(git log:*),Bash(git show *)')
        self.assertIn('  - `git log …`\n', surface)
        self.assertIn('  - `git show …`\n', surface)

    def test_an_exact_entry_keeps_its_whole_command_in_the_surface(self):
        _, surface = run_build_prompt(os.path.join(self.root, 'logs'), 'Bash(git branch -a)')
        self.assertIn('  - `git branch -a`\n', surface)

    def test_the_surface_names_the_write_tool(self):
        _, surface = run_build_prompt(os.path.join(self.root, 'logs'), 'Read')
        self.assertIn('Write each\n  file with the Write tool', surface)


if __name__ == '__main__':
    unittest.main()

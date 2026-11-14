"""The allow list and the tool surface that src/build-prompt.py writes for one run."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'src', 'build-prompt.py')
PR_URL = 'https://github.com/Jahia/example/pull/7'
REVIEW_NAME = 'pr-Jahia-example-7.review.json'


def run_build_prompt(log_dir, allowed_tools, disallowed_tools=''):
    """Run the script as the prep step does, and return the allow list and the surface it writes."""
    env = dict(os.environ, PR_URL=PR_URL, MARKER='<!-- marker -->',
               ALLOWED_TOOLS=allowed_tools, DISALLOWED_TOOLS=disallowed_tools)
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

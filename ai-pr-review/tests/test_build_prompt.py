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


def run_script(log_dir, allowed_tools, disallowed_tools='', review_round='', cortex_path=None, checkout='',
               reviewed_sha='', bin_dir=None):
    if cortex_path is None:
        cortex_path = os.path.join(os.path.dirname(log_dir), 'cortex')
    env = dict(os.environ, PR_URL=PR_URL, MARKER='<!-- marker -->', CORTEX_PATH=cortex_path,
               ALLOWED_TOOLS=allowed_tools, DISALLOWED_TOOLS=disallowed_tools, REVIEW_ROUND=review_round,
               CHECKOUT=checkout, REVIEWED_SHA=reviewed_sha)
    if bin_dir:
        env['PATH'] = bin_dir + os.pathsep + env['PATH']
    return subprocess.run([sys.executable, SCRIPT, log_dir], env=env, check=True,
                          capture_output=True, text=True)


def read_outputs(log_dir):
    with open(os.path.join(log_dir, 'allowed-tools.txt'), encoding='utf-8') as fh:
        allowed = fh.read().rstrip('\n')
    with open(os.path.join(log_dir, 'review.system.md'), encoding='utf-8') as fh:
        surface = fh.read()
    return allowed, surface


def run_build_prompt(log_dir, *args, **options):
    run_script(log_dir, *args, **options)
    return read_outputs(log_dir)


def make_checkout(path):
    git = ['git', '-C', path, '-c', 'user.name=test', '-c', 'user.email=test@example.com',
           '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null']
    subprocess.run(['git', 'init', '-q', path], check=True)
    subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'head'], check=True)
    return subprocess.run(git + ['rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()


def read_action_default(name):
    with open(os.path.join(os.path.dirname(os.path.dirname(SCRIPT)), 'action.yml'), encoding='utf-8') as fh:
        return re.search(rf"\n  {name}:\n(?:    .*\n)*?    default: '([^']*)'", fh.read()).group(1)


def select_bash_rules(rules):
    return [rule for rule in rules.split(',') if rule.startswith('Bash(')]


def matches(rule, command):
    # A model of the matcher of Claude Code, where `*` is any text and a trailing `:*` a prefix.
    pattern = rule[len('Bash('):-len(')')].replace('\\' * 4, '\\')
    if pattern.endswith(':*'):
        pattern = pattern[:-len(':*')] + '*'
    return re.fullmatch('.*'.join(map(re.escape, pattern.split('*'))), command, re.DOTALL) is not None


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
        default = read_action_default('disallowed_tools')
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

    def test_a_checkout_adds_the_git_reads_of_the_inspectors_with_its_literal_path(self):
        log_dir = os.path.join(self.root, 'logs')
        checkout = f'{self.root}/cortex//sources/example'
        allowed, _ = run_build_prompt(log_dir, 'Read', checkout=checkout, reviewed_sha=make_checkout(checkout))
        self.assertTrue(allowed.endswith(','.join(
            f'Bash(git -C {checkout} {verb}:*)' for verb in ('diff', 'log', 'show', 'grep', 'blame'))))

    def run_at_checkout(self, allowed_tools='Read', disallowed_tools=''):
        log_dir = os.path.join(self.root, 'logs')
        checkout = os.path.join(self.root, 'cortex', 'sources', 'example')
        allowed, surface = run_build_prompt(log_dir, allowed_tools, disallowed_tools, checkout=checkout,
                                            reviewed_sha=make_checkout(checkout))
        return checkout, allowed, self.read_denied(log_dir), surface

    def test_a_checkout_adds_the_fences_of_the_git_reads_to_any_deny_list(self):
        checkout, _, denied, _ = self.run_at_checkout('Read', 'Edit')
        fences = ['*--output*', 'grep *O*', 'grep *--op*', "*'*", '*"*', '*' + '\\' * 4 + '*', '*$*', '*`*', '*{*']
        self.assertEqual(denied, ','.join(
            ['Edit', f"Edit(/{os.path.join(self.root, 'cortex')}/**)"] + [f'Bash(git -C {checkout} {fence})' for fence in fences]))

    def test_the_fences_deny_each_escape_of_a_git_read(self):
        checkout, _, denied, _ = self.run_at_checkout()
        denied = select_bash_rules(denied)
        escapes = ['diff --output=/tmp/x', 'grep -lOsh x', 'grep --open-files-in-pager=sh x', 'log --out"put"=x',
                   "log --out'put'=x", 'log --out\\put=x', 'log $OPTION', 'log `echo x`', 'log --out{put,}=x']
        for escape in escapes:
            with self.subTest(escape=escape):
                self.assertTrue(any(matches(rule, f'git -C {checkout} {escape}') for rule in denied))

    def test_the_default_lists_of_the_action_allow_each_plain_read_and_no_global_option(self):
        checkout, allowed, denied, _ = self.run_at_checkout(read_action_default('allowed_tools'),
                                                            read_action_default('disallowed_tools'))
        allowed, denied = select_bash_rules(allowed), select_bash_rules(denied)
        for read in ('log --oneline -5', 'grep -n foo', 'diff origin/main...HEAD', 'blame README.md', 'show HEAD:a.md'):
            with self.subTest(read=read):
                command = f'git -C {checkout} {read}'
                self.assertTrue(any(matches(rule, command) for rule in allowed))
                self.assertFalse(any(matches(rule, command) for rule in denied))
        options = ('-c core.fsmonitor=sh diff HEAD', '--config-env=core.pager=X log -1', '--exec-path=/tmp show HEAD')
        for option in options:
            with self.subTest(option=option):
                self.assertFalse(any(matches(rule, f'git -C {checkout} {option}') for rule in allowed))

    def test_no_checkout_adds_no_git_rule(self):
        log_dir = os.path.join(self.root, 'logs')
        allowed, surface = run_build_prompt(log_dir, 'Read')
        self.assertNotIn('git -C', allowed)
        self.assertNotIn('git -C', self.read_denied(log_dir))
        self.assertIn('this run has no checkout of it', surface)

    def test_a_checkout_off_the_reviewed_head_adds_no_git_rule(self):
        checkout = os.path.join(self.root, 'cortex', 'sources', 'example')
        checkout_head = make_checkout(checkout)
        not_a_checkout = os.path.join(self.root, 'cortex', 'sources', 'plain')
        os.makedirs(not_a_checkout)
        missing = os.path.join(self.root, 'cortex', 'sources', 'missing')
        untypable = os.path.join(self.root, 'my work', 'example')
        untypable_head = make_checkout(untypable)
        head = 'f' * 40
        cases = (
            (checkout, head, f'the checkout {checkout} is at {checkout_head}, not at the reviewed head {head}'),
            (untypable, head, f'the checkout {untypable} is at {untypable_head}, not at the reviewed head {head}'),
            (checkout, '', 'the pre-fetch step read no reviewed head'),
            (not_a_checkout, head, f'git cannot read the head of the checkout {not_a_checkout}: fatal:'),
            (missing, head, f'git cannot read the head of the checkout {missing}: fatal:'),
        )
        for path, reviewed_sha, warning in cases:
            with self.subTest(path=path, reviewed_sha=reviewed_sha):
                log_dir = os.path.join(self.root, 'logs')
                result = run_script(log_dir, 'Read', checkout=path, reviewed_sha=reviewed_sha)
                allowed, surface = read_outputs(log_dir)
                self.assertNotIn('git -C', allowed)
                self.assertNotIn('git -C', self.read_denied(log_dir))
                self.assertNotIn('git -C', surface)
                self.assertIn('so review none of its files', surface)
                self.assertIn(f'::warning title=No git reads::{warning}', result.stderr)

    def test_a_head_that_git_cannot_read_names_the_error_of_git(self):
        bin_dir = os.path.join(self.root, 'bin')
        os.makedirs(bin_dir)
        checkout = os.path.join(self.root, 'cortex', 'sources', 'example')
        os.makedirs(checkout)
        for stderr, error in (('warning: x\\nfatal: dubious ownership\\nhint: y\\n', 'fatal: dubious ownership'),
                              ('', 'exit code 3')):
            with self.subTest(error=error):
                with open(os.path.join(bin_dir, 'git'), 'w', encoding='utf-8') as fh:
                    fh.write(f"#!/bin/sh\nprintf '{stderr}' >&2\nexit 3\n")
                os.chmod(os.path.join(bin_dir, 'git'), 0o755)
                result = run_script(os.path.join(self.root, 'logs'), 'Read', checkout=checkout, reviewed_sha='f' * 40,
                                    bin_dir=bin_dir)
                self.assertIn(f'git cannot read the head of the checkout {checkout}: {error}\n', result.stderr)

    def test_a_checkout_path_that_the_agent_cannot_type_adds_no_git_rule(self):
        for name in ('my work', 'star*'):
            with self.subTest(name=name):
                checkout = os.path.join(self.root, name, 'example')
                log_dir = os.path.join(self.root, 'logs')
                result = run_script(log_dir, 'Read', checkout=checkout, reviewed_sha=make_checkout(checkout))
                allowed, surface = read_outputs(log_dir)
                self.assertNotIn('git -C', allowed)
                self.assertNotIn('git -C', self.read_denied(log_dir))
                self.assertNotIn('git -C', surface)
                self.assertIn(f'`git` cannot run in the checkout at `{checkout}`', surface)
                self.assertIn('Read, Grep and Glob open its files, at the reviewed head', surface)
                self.assertIn(f'::warning title=No git reads::the agent cannot type the checkout path {checkout}',
                              result.stderr)

    def test_the_surface_states_the_git_reads_of_the_checkout(self):
        checkout, _, _, surface = self.run_at_checkout()
        self.assertIn(f'  - `git -C {checkout} grep …`\n', surface)
        self.assertIn(f'only as `git -C {checkout}`', surface)
        self.assertIn('The clone is blobless', surface)

    def test_the_surface_shows_the_backslash_that_a_fence_denies(self):
        checkout, _, _, surface = self.run_at_checkout()
        self.assertIn(f'  - `git -C {checkout} *\\*`\n', surface)

    def test_a_rule_that_mixes_a_wildcard_with_the_trailing_prefix_prints_a_warning(self):
        for allowed_tools, disallowed_tools, rule in (('Read', 'Bash(git -C * push:*)', 'Bash(git -C * push:*)'),
                                                      ('Bash(git -C * log:*)', 'Edit', 'Bash(git -C * log:*)')):
            with self.subTest(rule=rule):
                result = run_script(os.path.join(self.root, 'logs'), allowed_tools, disallowed_tools)
                self.assertIn(f'::warning title=Dead permission rule::{rule} matches no command', result.stderr)
        result = run_script(os.path.join(self.root, 'logs'), 'Bash(git log:*)', 'Bash(git -C * push *)')
        self.assertNotIn('Dead permission rule', result.stderr)

    def test_the_default_deny_list_of_the_action_mixes_no_wildcard_with_the_trailing_prefix(self):
        for name in ('allowed_tools', 'disallowed_tools'):
            self.assertEqual(re.findall(r'Bash\([^)]*\*[^)]*:\*\)', read_action_default(name)), [], name)

    def test_the_default_deny_list_of_the_action_denies_each_git_write_in_a_directory(self):
        denied = read_action_default('disallowed_tools').split(',')
        for write in ('push', 'commit', 'switch', 'checkout', 'reset', 'remote'):
            with self.subTest(write=write):
                self.assertIn(f'Bash(git -C * {write} *)', denied)
                self.assertIn(f'Bash(git -C * {write})', denied)

    def test_the_default_allow_list_of_the_action_grants_each_verb_of_pr_review(self):
        allowed = read_action_default('allowed_tools').split(',')
        for verb in ('lenses', 'number-lines', 'render', 'record'):
            self.assertIn(f'Bash(tools/pr-review/bin/pr-review {verb}:*)', allowed)


if __name__ == '__main__':
    unittest.main()

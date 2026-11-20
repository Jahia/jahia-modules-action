"""The report compares the dependencies of the base and the head, and writes one comment and the job summary."""

import contextlib
import io
import pathlib
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from report import (
    AllowlistError,
    Analysis,
    Dependency,
    RenderOptions,
    compile_allowlist,
    diff_dependencies,
    parse_direct,
    parse_third_party,
    read_analysis,
    render_report,
    run,
)

ALLOWLIST = compile_allowlist("Apache|MIT")
OPTIONS = RenderOptions(base_branch="main", base_found=True, show_checklist=False, command="mvn x")
BASE = Analysis(
    [
        Dependency("a:kept", "1.0", ("Apache 2",)),
        Dependency("a:bumped", "1.0", ("Apache 2",)),
        Dependency("a:dropped", "1.0", ("MIT",)),
        Dependency("a:relicensed", "1.0", ("Apache 2",)),
        Dependency("a:old-gpl", "1.0", ("GPL",)),
    ],
    {"a:kept", "a:bumped", "a:dropped"},
)
HEAD = Analysis(
    [
        Dependency("a:kept", "1.0", ("Apache 2",)),
        Dependency("a:bumped", "2.0", ("Apache 2",)),
        Dependency("a:relicensed", "1.0", ("GPL",)),
        Dependency("a:old-gpl", "1.1", ("GPL",)),
        Dependency("b:new-lgpl", "3.0", ("LGPL",)),
        Dependency("b:new-dual", "1.0", ("Apache 2", "GPL")),
    ],
    {"a:kept", "a:bumped", "b:new-dual"},
)
EMPTY = Analysis([], set())
REPORT = diff_dependencies(BASE, HEAD, ALLOWLIST)


def render(report, **changes) -> str:
    return render_report(report, RenderOptions(**{**OPTIONS.__dict__, **changes}))


def write_analysis(directory: pathlib.Path, third_party: str = "", direct: str = "", error: str = "") -> None:
    directory.mkdir(parents=True)
    for name, text in (("third-party.tsv", third_party), ("direct.txt", direct), ("error", error)):
        if text:
            (directory / name).write_text(text)


class TestTheParsing(unittest.TestCase):
    def test_reads_one_dependency_per_line_with_every_license(self):
        text = "org.hibernate:hibernate-core\t5.5.3.Final\tLGPL 2.1\ncom.zaxxer:HikariCP\t1.0-SNAPSHOT\tApache 2|GPL (v2)\n"
        self.assertEqual(
            parse_third_party(text),
            [
                Dependency("org.hibernate:hibernate-core", "5.5.3.Final", ("LGPL 2.1",)),
                Dependency("com.zaxxer:HikariCP", "1.0-SNAPSHOT", ("Apache 2", "GPL (v2)")),
            ],
        )

    def test_keeps_a_dependency_that_declares_no_license(self):
        self.assertEqual(parse_third_party("org.foo:bar\t1.0\t\r\n"), [Dependency("org.foo:bar", "1.0", ())])

    def test_merges_one_artifact_that_two_modules_resolve(self):
        text = "g:guava\t31.0\tApache 2\ng:guava\t30.0\tApache 2|MIT\ng:guava\t31.0\tApache 2\n"
        self.assertEqual(parse_third_party(text), [Dependency("g:guava", "30.0, 31.0", ("Apache 2", "MIT"))])

    def test_reads_the_direct_dependencies_of_every_module_with_their_version(self):
        text = "\n".join(
            [
                "The following files have been resolved:",
                "   org.jahia.keymaker:keymaker-common:jar:2.1.0-SNAPSHOT:compile -- module keymaker.common (auto)",
                "   commons-lang:commons-lang:jar:2.5:compile",
                "The following files have been resolved:",
                "   io.netty:netty-transport-native-epoll:jar:linux-x86_64:4.1.100.Final:runtime",
                "   none",
            ]
        )
        self.assertEqual(
            parse_direct(text),
            {
                "org.jahia.keymaker:keymaker-common": "2.1.0-SNAPSHOT",
                "commons-lang:commons-lang": "2.5",
                "io.netty:netty-transport-native-epoll": "4.1.100.Final",
            },
        )

    def test_reads_the_reason_analyze_sh_wrote(self):
        with tempfile.TemporaryDirectory() as directory:
            write_analysis(pathlib.Path(directory, "head"), error="Maven wrote no license report.\n")
            self.assertEqual(read_analysis(pathlib.Path(directory, "head")).error, "Maven wrote no license report.")

    def test_reads_a_latin_1_report(self):
        with tempfile.TemporaryDirectory() as directory:
            pathlib.Path(directory, "head").mkdir()
            pathlib.Path(directory, "head", "third-party.tsv").write_bytes("g:x\t1.0\tLicence Fran\u00e7aise\n".encode("latin-1"))
            analysis = read_analysis(pathlib.Path(directory, "head"))
        self.assertEqual(analysis.dependencies, [Dependency("g:x", "1.0", ("Licence Fran\u00e7aise",))])

    def test_keeps_a_direct_dependency_that_the_license_goal_excludes_unchecked(self):
        with tempfile.TemporaryDirectory() as directory:
            write_analysis(pathlib.Path(directory, "head"), "a:b\t1.0\tMIT\n", "   org.jahia:core:jar:8.2.0:compile\n")
            analysis = read_analysis(pathlib.Path(directory, "head"))
        self.assertIn(Dependency("org.jahia:core", "8.2.0", (), False), analysis.dependencies)


class TestTheAllowlist(unittest.TestCase):
    allowlist = compile_allowlist("MIT|The Apache|BSD|EDL 1\\.0\n")

    def test_matches_a_license_case_insensitively(self):
        self.assertTrue(self.allowlist.search("mit license"))
        self.assertTrue(self.allowlist.search("EDL 1.0"))

    def test_rejects_a_license_it_does_not_name(self):
        self.assertFalse(self.allowlist.search("GNU General Public License"))
        self.assertFalse(compile_allowlist("").search("GPL"))

    def test_always_allows_a_jahia_license(self):
        self.assertTrue(self.allowlist.search("Jahia Sustainable Software License"))
        self.assertTrue(compile_allowlist("").search("Jahia"))

    def test_names_the_allowlist_when_it_does_not_compile(self):
        with self.assertRaisesRegex(AllowlistError, "The license allowlist is not a valid"):
            compile_allowlist("MIT|(Apache")


class TestTheDiff(unittest.TestCase):
    def test_lists_each_dependency_that_changed(self):
        self.assertEqual(
            [(change.key, change.kind, change.direct, change.allowed) for change in REPORT.changes],
            [
                ("a:bumped", "updated", True, True),
                ("a:dropped", "removed", True, None),
                ("a:old-gpl", "updated", False, False),
                ("a:relicensed", "license", False, False),
                ("b:new-dual", "added", True, True),
                ("b:new-lgpl", "added", False, False),
            ],
        )

    def test_lists_an_incompatible_license_the_pull_request_introduces(self):
        self.assertEqual([dependency.key for dependency in REPORT.introduced], ["a:relicensed", "b:new-lgpl"])

    def test_keeps_apart_an_incompatible_license_the_base_had(self):
        self.assertEqual([dependency.key for dependency in REPORT.existing], ["a:old-gpl"])

    def test_reads_no_license_change_from_a_new_order_of_the_modules(self):
        before = Analysis(parse_third_party("g:x\t1.0\tApache 2|MIT\n"), set())
        after = Analysis(parse_third_party("g:x\t1.0\tMIT\ng:x\t1.0\tApache 2\n"), set())
        self.assertEqual(diff_dependencies(before, after, ALLOWLIST).changes, [])

    def test_counts_a_dependency_with_no_license_as_incompatible(self):
        report = diff_dependencies(EMPTY, Analysis([Dependency("c:bare", "1.0", ())], set()), ALLOWLIST)
        self.assertEqual([dependency.key for dependency in report.introduced], ["c:bare"])

    def test_judges_no_license_of_an_unchecked_update(self):
        before = Analysis([Dependency("org.jahia:core", "8.1", (), False)], {"org.jahia:core"})
        after = Analysis([Dependency("org.jahia:core", "8.2", (), False)], {"org.jahia:core"})
        report = diff_dependencies(before, after, ALLOWLIST)
        self.assertEqual([(change.kind, change.allowed) for change in report.changes], [("updated", None)])
        self.assertEqual(report.introduced, [])
        self.assertIn("| 8.1 | 8.2 | not checked |  |", render(report))


class TestTheRender(unittest.TestCase):
    def test_puts_the_direct_changes_in_the_table(self):
        visible = render(REPORT).split("<details>", 1)[0]
        self.assertIn("[a:bumped](https://mvnrepository.com/artifact/a/bumped) | Updated | 1.0 | 2.0 | Apache 2 | ✅ |", visible)
        self.assertIn("| [a:dropped](https://mvnrepository.com/artifact/a/dropped) | Removed | 1.0 |  | MIT |  |", visible)
        self.assertNotIn("b:new-lgpl](", visible)

    def test_folds_the_transitive_changes(self):
        folded = render(REPORT).split("<details>", 1)[1]
        self.assertIn("<summary>3 transitive changes</summary>", folded)
        self.assertIn("[b:new-lgpl](https://mvnrepository.com/artifact/b/new-lgpl) | Added |  | 3.0 | LGPL | ❌ |", folded)

    def test_lists_the_introduced_licenses_above_the_changes(self):
        body = render(REPORT)
        self.assertLess(0, body.index("### Incompatible licenses introduced"))
        self.assertLess(body.index("### Incompatible licenses introduced"), body.index("### Changes"))
        self.assertIn("- `b:new-lgpl:3.0`: LGPL", body)

    def test_folds_the_incompatible_licenses_the_base_had(self):
        self.assertIn("<summary>1 incompatible license already on `main`</summary>", render(REPORT))

    def test_shows_the_checklist_only_when_asked(self):
        self.assertNotIn("- [ ]", render(REPORT))
        self.assertIn("- [ ] Did you check if the licenses", render(REPORT, show_checklist=True))

    def test_says_when_the_base_branch_has_no_pom(self):
        self.assertIn("`main` has no POM at this path", render(REPORT, base_found=False))

    def test_says_that_nothing_changed(self):
        body = render(diff_dependencies(BASE, BASE, ALLOWLIST))
        self.assertIn("No dependency and no license changed compared with `main`.", body)
        self.assertNotIn("### Changes", body)

    def test_counts_the_transitive_changes_it_leaves_out(self):
        body = render_report(REPORT, OPTIONS, list_transitive=False)
        self.assertNotIn("b:new-lgpl](", body)
        self.assertIn("3 transitive changes, too many for a comment", body)

    def test_renders_the_markdown_and_html_of_a_license_as_text(self):
        hostile = Dependency("d:evil", "1.0", ("<img src=x> [click](http://evil) *GPL* @jahia/security &#64;team https://evil",))
        body = render(diff_dependencies(EMPTY, Analysis([hostile], {"d:evil"}), ALLOWLIST))
        self.assertNotRegex(body, r"(^|[^\\])<img")
        self.assertIn("\\<img src=x\\> \\[click\\]\\(http:\u200b//evil\\) \\*GPL\\* @\u200bjahia/security &amp;\\#64;team https:\u200b//evil", body)

    def test_links_each_version_of_a_split_artifact(self):
        split = Dependency("g:guava", "30.0, 31.0", ("Apache 2",))
        body = render(diff_dependencies(EMPTY, Analysis([split], {"g:guava"}), ALLOWLIST))
        self.assertIn("[Snyk 30.0](https://security.snyk.io/package/maven/g:guava/30.0)", body)
        self.assertIn("[OSS Index 31.0](https://ossindex.sonatype.org/component/pkg:maven/g/guava@31.0)", body)
        self.assertIsNone(re.search(r"\]\([^)]* [^)]*\)", body))


class TestTheRun(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory)
        (self.directory / "allowlist.txt").write_text("Apache|MIT")
        self.env = {
            "REPORT_DIR": str(self.directory),
            "ALLOWLIST_FILE": str(self.directory / "allowlist.txt"),
            "BASE_BRANCH": "main",
            "BASE_FOUND": "true",
            "GITHUB_STEP_SUMMARY": str(self.directory / "summary.md"),
            "GITHUB_OUTPUT": str(self.directory / "output"),
        }

    def run_report(self, **changes: str) -> str:
        run({**self.env, **changes})
        return (self.directory / "comment.md").read_text()

    def output(self) -> str:
        return (self.directory / "output").read_text()

    def test_says_why_the_analysis_of_the_pull_request_failed(self):
        write_analysis(self.directory / "head", error="Maven failed on pom.xml.")
        comment = self.run_report()
        self.assertIn("- The analysis of the pull request failed: Maven failed on pom.xml.", comment)
        self.assertIn("This check never blocks the pull request.", comment)
        self.assertEqual(self.output(), "has_changes=true\n")

    def test_says_why_the_analysis_of_the_base_failed(self):
        write_analysis(self.directory / "head", "a:b\t1.0\tMIT\n")
        write_analysis(self.directory / "base", error="Maven failed on pom.xml.")
        self.assertIn("- The analysis of `main` failed: Maven failed on pom.xml.", self.run_report())

    def test_says_the_allowlist_file_is_missing(self):
        write_analysis(self.directory / "head", "a:b\t1.0\tMIT\n")
        self.assertIn("No such file", self.run_report(ALLOWLIST_FILE=str(self.directory / "missing.txt")))

    def test_says_the_allowlist_does_not_compile(self):
        write_analysis(self.directory / "head", "a:b\t1.0\tMIT\n")
        (self.directory / "allowlist.txt").write_text("MIT|(Apache")
        self.assertIn("The license allowlist is not a valid", self.run_report())

    def test_warns_with_the_plain_text_of_a_problem(self):
        write_analysis(self.directory / "head", "a:b\t1.0\tMIT\n")
        write_analysis(self.directory / "base", error="Maven failed on core/pom.xml.")
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            self.run_report()
        self.assertIn("::warning::The analysis of main failed: Maven failed on core/pom.xml.\n", log.getvalue())

    def test_ignores_the_base_when_it_has_no_pom(self):
        write_analysis(self.directory / "head", "a:b\t1.0\tMIT\n")
        self.assertIn("`main` has no POM at this path", self.run_report(BASE_FOUND="false"))

    def test_states_no_change_for_the_comment_step(self):
        write_analysis(self.directory / "head", "a:b\t1.0\tMIT\n")
        write_analysis(self.directory / "base", "a:b\t1.0\tMIT\n")
        self.run_report()
        self.assertEqual(self.output(), "has_changes=false\n")

    def test_shortens_a_comment_too_long_for_github(self):
        lines = "".join(f"g:transitive-{index}\t1.0\tApache 2\n" for index in range(400))
        write_analysis(self.directory / "head", lines)
        comment = self.run_report(BASE_FOUND="false")
        self.assertLess(len(comment), 65536)
        self.assertIn("400 transitive changes, too many for a comment", comment)
        self.assertGreater(len((self.directory / "summary.md").read_text()), 65536)

    def test_points_to_the_summary_when_even_the_short_comment_is_too_long(self):
        direct = "".join(f"   g:direct-{index}:jar:1.0:compile\n" for index in range(400))
        lines = "".join(f"g:direct-{index}\t1.0\tApache 2\n" for index in range(400))
        write_analysis(self.directory / "head", lines, direct)
        comment = self.run_report(BASE_FOUND="false")
        self.assertIn("The report is too long for a comment", comment)


if __name__ == "__main__":
    unittest.main()

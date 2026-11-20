"""Compare the Java dependencies and licenses of a pull request with its base branch.

Reads what analyze.sh wrote in REPORT_DIR/base and REPORT_DIR/head, writes the report to the job
summary, and writes the comment that the next step of action.yml keeps on the pull request. The
check informs and never blocks the pull request, so the script always exits 0.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# Below the size GitHub accepts for a comment, with room for the header the comment action adds.
_COMMENT_LIMIT = 65000
TITLE = "## Java dependencies"
CHECKLIST = [
    "- [ ] Did you check the impact on the platform?",
    "- [ ] Did you check if these libraries are still supported?",
    "- [ ] Did you check if there are security vulnerabilities?",
    "- [ ] Did you check if the licenses are compatible with our products?",
    "",
]
LABELS = {
    "added": "Added",
    "removed": "Removed",
    "updated": "Updated",
    "license": "License changed",
}
TABLE_HEADER = [
    "| Dependency | Change | Old version | New version | Licenses | Allowed | Details |",
    "| -- | -- | -- | -- | -- | -- | -- |",
]


class AllowlistError(ValueError):
    """The license allowlist does not compile."""


@dataclass(frozen=True)
class Dependency:
    key: str  # groupId:artifactId, the identity a version change keeps
    version: str
    licenses: tuple[str, ...]
    checked: bool = True  # False for a direct dependency the license goal excludes, such as org.jahia


@dataclass(frozen=True)
class Analysis:
    dependencies: list[Dependency]
    direct: set[str]
    error: str = ""  # the reason analyze.sh gave when Maven failed or wrote no report


@dataclass(frozen=True)
class Change:
    kind: str
    key: str
    before: Dependency | None
    after: Dependency | None
    direct: bool
    allowed: bool | None  # None when nothing ships to judge, or the license goal excludes it


@dataclass(frozen=True)
class Report:
    changes: list[Change]
    introduced: list[Dependency]  # incompatible on the head, and absent or compatible on the base
    existing: list[Dependency]  # incompatible on the head and already on the base


def _merge_versions(versions: set[str]) -> str:
    return ", ".join(sorted(versions))


def parse_third_party(text: str) -> list[Dependency]:
    """Reads "groupId:artifactId<TAB>version<TAB>license|license", and merges an artifact that several modules resolve."""
    versions: dict[str, set[str]] = {}
    licenses: dict[str, dict[str, None]] = {}
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            continue
        key, version, names = fields
        versions.setdefault(key, set()).add(version)
        licenses.setdefault(key, {}).update(dict.fromkeys(name for name in names.split("|") if name))
    return [Dependency(key, _merge_versions(versions_of_key), tuple(sorted(licenses[key]))) for key, versions_of_key in versions.items()]


def parse_direct(text: str) -> dict[str, str]:
    """Reads dependency:list, whose lines read "   groupId:artifactId:type[:classifier]:version:scope"."""
    versions: dict[str, set[str]] = {}
    for line in text.splitlines():
        if not re.match(r"\s+[^:\s]+:[^:\s]+:\S+", line):
            continue
        fields = line.split()[0].split(":")
        versions.setdefault(f"{fields[0]}:{fields[1]}", set()).add(fields[-2])
    return {key: _merge_versions(versions_of_key) for key, versions_of_key in versions.items()}


def _decode(content: bytes) -> str:
    # The plugin writes the encoding of the project, and Latin-1 reads any byte.
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def read_analysis(directory: Path) -> Analysis:
    """A directory analyze.sh never wrote, as for a base branch with no POM, has no dependency."""

    def read(name: str) -> str:
        path = directory / name
        return _decode(path.read_bytes()) if path.is_file() else ""

    dependencies = parse_third_party(read("third-party.tsv"))
    direct = parse_direct(read("direct.txt"))
    licensed_keys = {dependency.key for dependency in dependencies}
    unlicensed_direct = [Dependency(key, version, (), False) for key, version in direct.items() if key not in licensed_keys]
    return Analysis(dependencies + unlicensed_direct, set(direct), read("error").strip())


def compile_allowlist(text: str) -> re.Pattern[str]:
    """Compiles the regular expression of the allowlist file. A license that names Jahia is always allowed."""
    allowlist = text.strip()
    try:
        return re.compile(f"Jahia|{allowlist}" if allowlist else "Jahia", re.IGNORECASE)
    except re.error as error:
        raise AllowlistError(f"The license allowlist is not a valid Python regular expression: {error}") from error


def _is_allowed(dependency: Dependency, allowlist: re.Pattern[str]) -> bool:
    # A dependency under several licenses can be used under any one of them.
    return not dependency.checked or any(allowlist.search(license) for license in dependency.licenses)


def _classify_change(before: Dependency | None, after: Dependency | None) -> str | None:
    if before is None:
        return "added"
    if after is None:
        return "removed"
    if before.version != after.version:
        return "updated"
    if before.licenses != after.licenses:
        return "license"
    return None


def diff_dependencies(base: Analysis, head: Analysis, allowlist: re.Pattern[str]) -> Report:
    base_by_key = {dependency.key: dependency for dependency in base.dependencies}
    head_by_key = {dependency.key: dependency for dependency in head.dependencies}
    changes = []
    for key in sorted(base_by_key.keys() | head_by_key.keys()):
        before, after = base_by_key.get(key), head_by_key.get(key)
        kind = _classify_change(before, after)
        if kind is None:
            continue
        allowed = _is_allowed(after, allowlist) if after is not None and after.checked else None
        changes.append(Change(kind, key, before, after, key in head.direct or key in base.direct, allowed))

    def was_incompatible(key: str) -> bool:
        return key in base_by_key and not _is_allowed(base_by_key[key], allowlist)

    incompatible = [dependency for dependency in head.dependencies if not _is_allowed(dependency, allowlist)]
    return Report(
        changes,
        [dependency for dependency in incompatible if not was_incompatible(dependency.key)],
        [dependency for dependency in incompatible if was_incompatible(dependency.key)],
    )


def _escape(text: str) -> str:
    # A license comes from the POM of a third party, so its Markdown, HTML, mentions and links render as text.
    markdown = re.sub(r"([\\`*_\[\]()<>|#!~])", r"\\\1", text.replace("&", "&amp;"))
    return markdown.replace("@", "@\u200b").replace("://", ":\u200b//")


def _format_plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _render_details(summary: str, lines: list[str]) -> list[str]:
    return ["<details>", f"<summary>{summary}</summary>", "", *lines, "", "</details>"]


def _render_links(key: str, versions: str) -> str:
    # An artifact resolved at several versions gets links for each, labelled.
    group_id, _, artifact_id = key.partition(":")
    versions_list = [version for version in versions.split(", ") if version]

    def label(name: str, version: str) -> str:
        return f"{name} {version}" if len(versions_list) > 1 else name

    links = []
    for version in versions_list:
        links.append(f"[{label('Snyk', version)}](https://security.snyk.io/package/maven/{key}/{version})")
        links.append(
            f"[{label('OSS Index', version)}]"
            f"(https://ossindex.sonatype.org/component/pkg:maven/{group_id}/{artifact_id}@{version})"
        )
    return " · ".join(links)


def _render_licenses(dependency: Dependency) -> str:
    return _escape(", ".join(dependency.licenses)) if dependency.checked else "not checked"


def _render_row(change: Change) -> str:
    group_id, _, artifact_id = change.key.partition(":")
    current = change.after or change.before
    status = "" if change.allowed is None else "✅" if change.allowed else "❌"
    cells = [
        f"[{change.key}](https://mvnrepository.com/artifact/{group_id}/{artifact_id})",
        LABELS[change.kind],
        _escape(change.before.version if change.before else ""),
        _escape(change.after.version if change.after else ""),
        _render_licenses(current),
        status,
        _render_links(change.key, current.version),
    ]
    return f"| {' | '.join(cells)} |"


def _render_table(changes: list[Change]) -> list[str]:
    return TABLE_HEADER + [_render_row(change) for change in changes]


def _render_list_item(dependency: Dependency) -> str:
    return f"- `{dependency.key}:{dependency.version}`: {_render_licenses(dependency)}"


def _render_reproduce(command: str) -> list[str]:
    return [f"To reproduce, run `{command}`."] if command else []


@dataclass(frozen=True)
class RenderOptions:
    base_branch: str
    base_found: bool
    show_checklist: bool
    command: str


def render_report(report: Report, options: RenderOptions, list_transitive: bool = True) -> str:
    """With no change, the body says so, which replaces an earlier report."""
    base = f"`{options.base_branch}`"
    direct = [change for change in report.changes if change.direct]
    transitive = [change for change in report.changes if not change.direct]
    lines = [TITLE, ""]
    if not report.changes:
        lines += [f"No dependency and no license changed compared with {base}.", ""]
    else:
        if not options.base_found:
            lines += [f"> {base} has no POM at this path, so every dependency counts as added.", ""]
        if options.show_checklist:
            lines += CHECKLIST
        if report.introduced:
            lines += ["### Incompatible licenses introduced", ""]
            lines += [_render_list_item(dependency) for dependency in report.introduced] + [""]
        lines += ["### Changes", ""]
        lines += (_render_table(direct) if direct else ["No direct dependency changed."]) + [""]
        summary = _format_plural(len(transitive), "transitive change")
        if transitive and list_transitive:
            lines += _render_details(summary, _render_table(transitive)) + [""]
        elif transitive:
            lines += [f"{summary}, too many for a comment: the job summary of the run lists them.", ""]
    if report.existing:
        summary = f"{_format_plural(len(report.existing), 'incompatible license')} already on {base}"
        lines += _render_details(summary, [_render_list_item(dependency) for dependency in report.existing]) + [""]
    return "\n".join(lines + _render_reproduce(options.command)).rstrip()


def _render_problems(problems: list[str], command: str) -> str:
    # The body when the comparison could not run, which replaces an earlier report, now out of date.
    lines = [TITLE, "", "The dependencies were not compared, so this comment lists no change:", ""]
    lines += [f"- {problem}" for problem in problems]
    lines += ["", "The log of the job shows the detail. This check never blocks the pull request."]
    reproduce = _render_reproduce(command)
    return "\n".join(lines + ([""] + reproduce if reproduce else []))


def _fit_comment(bodies: list[str]) -> str:
    # The first body GitHub accepts as a comment.
    for body in bodies:
        if len(body) <= _COMMENT_LIMIT:
            return body
    return f"{TITLE}\n\nThe report is too long for a comment: the job summary of the run shows it."


def _warn(message: str) -> None:
    workflow_line = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::warning::{workflow_line}", flush=True)


def _append(path: str, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as target:
            target.write(text)


def run(env: dict[str, str]) -> None:
    """Writes the report to the job summary, and the comment to REPORT_DIR/comment.md for the comment step."""
    report_dir = Path(env.get("REPORT_DIR", ""))
    options = RenderOptions(
        base_branch=env.get("BASE_BRANCH", ""),
        base_found=env.get("BASE_FOUND") == "true",
        show_checklist=env.get("SHOW_CHECKLIST") == "true",
        command=env.get("LICENSE_COMMAND", ""),
    )
    base = read_analysis(report_dir / "base")
    head = read_analysis(report_dir / "head")

    problems = []  # each a Markdown prefix and the plain text a tool wrote
    if head.error:
        problems.append(("The analysis of the pull request failed: ", head.error))
    if options.base_found and base.error:
        problems.append((f"The analysis of `{options.base_branch}` failed: ", base.error))
    try:
        allowlist = compile_allowlist(Path(env.get("ALLOWLIST_FILE", "")).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        problems.append(("", str(error)))

    if problems:
        body = _render_problems([prefix + _escape(text) for prefix, text in problems], options.command)
        comment = _fit_comment([body])
        # A comparison that did not run is news too, so it creates the comment.
        has_changes = True
    else:
        report = diff_dependencies(base, head, allowlist)
        body = render_report(report, options)
        comment = _fit_comment([body, render_report(report, options, list_transitive=False)])
        has_changes = bool(report.changes)

    print(body, flush=True)
    _append(env.get("GITHUB_STEP_SUMMARY", ""), body + "\n")
    (report_dir / "comment.md").write_text(comment, encoding="utf-8")
    _append(env.get("GITHUB_OUTPUT", ""), f"has_changes={str(has_changes).lower()}\n")
    for prefix, text in problems:
        _warn(prefix.replace("`", "") + text)


if __name__ == "__main__":
    try:
        run(dict(os.environ))
    except Exception as error:  # noqa: BLE001 - the check never blocks the pull request
        _warn(f"The dependencies check did not complete, and blocks nothing: {error}")

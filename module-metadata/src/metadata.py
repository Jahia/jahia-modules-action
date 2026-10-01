#!/usr/bin/env python3
"""Read what a Jahia module repository states about itself, and emit it as workflow outputs.

Sources, in this order of authority: pom.xml (and the submodule poms of a reactor), package.json,
mise.toml, the tests/ folder, and .jahia.yml. The .jahia.yml has two sections: `repository:` is read
from the default branch's copy whatever branch the run is on, `branch:` from the checkout itself.
"""
import argparse
import json
import os
import re
import sys
import tomllib
import xml.etree.ElementTree as ET

try:
    import yaml
except ImportError:  # the action installs PyYAML when the runner lacks it
    yaml = None

POM_NS = {"m": "http://maven.apache.org/POM/4.0.0"}
MODULES_PARENT = ("org.jahia.modules", "jahia-modules")
EXCLUDED_GROUPS = {"org.jahia.test", "org.jahia.samples"}
EXCLUDED_DIRS = {"test", "tests", "test-modules", "samples", "examples"}
EXCLUDED_TOKENS = ("example", "sample", "test")  # a path segment containing one of these is not a delivered module
AUDIT_LEVELS = ("low", "moderate", "high", "critical")

# .jahia.yml, phase 1. A key absent from this tree is refused, so a typo cannot fall back to a default.
SCHEMA = {
    "repository": {
        "module": str,
        "maintenance-branches": list,
        "tests": {"testrail-project": str, "incident-service": str},
    },
    "branch": {
        "ci": {"runner": str},
        "audit": {"level": str},
        "lint": {"max-warnings": int},
        "tests": {"exclude-profiles": list, "timeout-job": int, "timeout-step": int},
    },
}

DEFAULTS = {
    "runner": "ubuntu-latest",
    "audit-level": "critical",
    "max-warnings": 1,
    "timeout-job": 75,
    "timeout-step": 60,
}


class MetadataError(Exception):
    pass


# --- pom.xml -------------------------------------------------------------------------------------

def _text(el):
    return el.text.strip() if el is not None and el.text else None


def read_pom(path):
    root = ET.parse(path).getroot()
    get = lambda q: _text(root.find(q, POM_NS))
    props_el = root.find("m:properties", POM_NS)
    props = {c.tag.split("}")[1]: (c.text or "").strip() for c in (props_el if props_el is not None else [])}
    plugins = {_text(p.find("m:artifactId", POM_NS)) for p in root.findall(".//m:plugin", POM_NS)}
    signed = "jahia-module-signature" in props or any(el.tag.endswith("}Jahia-Signature") or el.tag == "Jahia-Signature" for el in root.iter())
    return {
        "artifactId": get("m:artifactId"),
        "groupId": get("m:groupId") or get("m:parent/m:groupId"),
        "packaging": get("m:packaging") or "jar",
        "parent": (get("m:parent/m:groupId"), get("m:parent/m:artifactId"), get("m:parent/m:version")),
        "modules": [m.text.strip() for m in root.findall("m:modules/m:module", POM_NS) if m.text],
        "frontend": "frontend-maven-plugin" in plugins,
        "signed": signed,
    }


def read_reactor(root_dir, pom):
    subs = []
    for rel in pom["modules"]:
        sub_path = os.path.join(root_dir, rel, "pom.xml")
        if not os.path.exists(sub_path):
            continue
        sub = read_pom(sub_path)
        sub["path"] = rel
        parts = rel.replace("\\", "/").split("/")
        sub["excluded"] = (bool(set(parts) & EXCLUDED_DIRS) or sub["groupId"] in EXCLUDED_GROUPS
                           or any(tok in seg for seg in parts for tok in EXCLUDED_TOKENS))
        subs.append(sub)
    return subs


# --- small readers --------------------------------------------------------------------------------

def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_mise(path):
    with open(path, "rb") as f:
        tools = tomllib.load(f).get("tools") or {}
    out = {}
    for k, v in tools.items():
        if isinstance(v, list):
            v = v[0] if v else ""
        if isinstance(v, dict):
            v = v.get("version", "")
        out[k] = str(v)
    return out


def read_yaml(path):
    if yaml is None:
        raise MetadataError("PyYAML is required to read %s" % path)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def java_major(spec):
    """'temurin-8.0.504' -> 8, 'temurin-17' -> 17, '11' -> 11, '1.8' -> 8."""
    m = re.search(r"(\d+(?:\.\d+)*)", spec or "")
    if not m:
        return None
    parts = m.group(1).split(".")
    return int(parts[1]) if parts[0] == "1" and len(parts) > 1 else int(parts[0])


# --- .jahia.yml -----------------------------------------------------------------------------------

def check_config(node, schema, path=""):
    if not isinstance(node, dict):
        raise MetadataError(".jahia.yml: '%s' must be a mapping" % (path or "<root>"))
    for key, value in node.items():
        here = f"{path}.{key}" if path else key
        if key not in schema:
            raise MetadataError(".jahia.yml: unknown key '%s' (known here: %s)" % (here, ", ".join(sorted(schema))))
        expected = schema[key]
        if isinstance(expected, dict):
            check_config(value, expected, here)
        elif not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            raise MetadataError(".jahia.yml: '%s' must be a %s" % (here, expected.__name__))
        elif expected is list and not all(isinstance(x, str) for x in value):
            raise MetadataError(".jahia.yml: '%s' must be a list of strings" % here)
    return node


def load_config(local_path, default_copy_path):
    """repository: from the default branch's copy; branch: from the checkout."""
    local = check_config(read_yaml(local_path), SCHEMA) if local_path and os.path.exists(local_path) else {}
    if default_copy_path and os.path.exists(default_copy_path):
        default_copy = check_config(read_yaml(default_copy_path), SCHEMA)
    else:
        default_copy = local
    repo = default_copy.get("repository") or {}
    branch = local.get("branch") or {}
    level = (branch.get("audit") or {}).get("level")
    if level and level not in AUDIT_LEVELS:
        raise MetadataError(".jahia.yml: branch.audit.level must be one of %s" % ", ".join(AUDIT_LEVELS))
    return repo, branch


# --- tests/ ---------------------------------------------------------------------------------------

def read_tests(root_dir, excluded_profiles):
    tests = os.path.join(root_dir, "tests")
    out = {"has-tests": False, "profiles": [], "manifest-pr": "", "manifest-merge": "", "cluster": False, "test-module": "none"}
    if not os.path.isdir(tests):
        return out
    names = sorted(os.listdir(tests))
    configs = [n for n in names if re.fullmatch(r"cypress\.config[^/]*\.(ts|js)", n)]
    out["has-tests"] = bool(configs)
    out["profiles"] = [n for n in names if re.fullmatch(r"cypress\.config-[^/]+\.(ts|js)", n)
                       and n not in excluded_profiles and re.sub(r"^cypress\.config-|\.(ts|js)$", "", n) not in excluded_profiles]
    if "provisioning-manifest-build.yml" in names:
        out["manifest-pr"] = "provisioning-manifest-build.yml"
    if "provisioning-manifest-snapshot.yml" in names:
        out["manifest-merge"] = "provisioning-manifest-snapshot.yml"
    if os.path.exists(os.path.join(tests, "jahia-module", "pom.xml")):
        out["test-module"] = "mvn"
    elif os.path.exists(os.path.join(tests, "jahia-module", "package.json")):
        out["test-module"] = "javascript"
    compose = os.path.join(tests, "docker-compose.yml")
    browsing = 0
    if os.path.exists(compose) and yaml is not None:
        try:
            services = (read_yaml(compose).get("services") or {})
            browsing = sum(1 for s in services if str(s).startswith("jahia-browsing"))
        except Exception:
            browsing = 0
    out["cluster"] = "docker-compose-cluster.yml" in names or browsing >= 2
    return out


# --- the whole thing ------------------------------------------------------------------------------

def collect(root_dir, ref_name, default_branch, default_config, image_os="resolute"):
    out = {}
    pom_path = os.path.join(root_dir, "pom.xml")
    pkg_path = os.path.join(root_dir, "package.json")
    mise_path = os.path.join(root_dir, "mise.toml")
    repo_cfg, branch_cfg = load_config(os.path.join(root_dir, ".jahia.yml"), default_config)
    pom = read_pom(pom_path) if os.path.exists(pom_path) else None
    pkg = read_json(pkg_path) if os.path.exists(pkg_path) else None
    mise = read_mise(mise_path) if os.path.exists(mise_path) else {}
    if pom is None and pkg is None:
        raise MetadataError("neither pom.xml nor package.json at the repository root: not a module")

    out["build-tool"] = "maven" if pom else "javascript"
    out["java"] = mise.get("java", "")
    out["node"] = mise.get("node", "")
    out["yarn"] = mise.get("yarn", "")
    out["parent-version"] = ""
    out["signature-poms"] = []

    if pom:
        if pom["parent"][:2] == MODULES_PARENT:
            out["parent-version"] = pom["parent"][2] or ""
        if pom["packaging"] == "pom":
            subs = read_reactor(root_dir, pom)
            candidates = [s for s in subs if s["signed"] and not s["excluded"]]
            out["signature-poms"] = [f'{s["path"]}/pom.xml' for s in subs if s["signed"]]
            declared = repo_cfg.get("module")
            if declared:
                match = [s for s in subs if s["artifactId"] == declared]
                if not match:
                    raise MetadataError("repository.module '%s' names no submodule of the reactor" % declared)
                out["module-id"] = declared
            elif len(candidates) == 1:
                out["module-id"] = candidates[0]["artifactId"]
            elif not candidates:
                raise MetadataError("reactor with no signed submodule: declare repository.module in .jahia.yml")
            else:
                raise MetadataError("reactor with several signed submodules (%s): declare repository.module in .jahia.yml"
                                    % ", ".join(s["artifactId"] for s in candidates))
            out["has-frontend"] = pom["frontend"] or pkg is not None or any(s["frontend"] for s in subs)
        else:
            out["module-id"] = pom["artifactId"]
            out["signature-poms"] = ["pom.xml"] if pom["signed"] else []
            out["has-frontend"] = pom["frontend"] or pkg is not None
        if not out["java"]:
            raise MetadataError("mise.toml declares no java: a Maven module must state the JDK it builds with")
        major = java_major(out["java"])
        out["cache-image"] = f"ghcr.io/jahia/jahia-docker-mvn-cache:{major}-jdk-{image_os}-mvn-loaded"
    else:
        out["module-id"] = re.sub(r"^@[^/]+/", "", pkg.get("name", ""))
        out["has-frontend"] = True
        out["cache-image"] = ""

    jahia_major = (out["parent-version"] or "8").split(".")[0]
    out["jahia-image"] = f"ghcr.io/jahia/jahia-ee-dev:{jahia_major}-SNAPSHOT"

    tests_cfg = branch_cfg.get("tests") or {}
    tests = read_tests(root_dir, set(tests_cfg.get("exclude-profiles") or []))
    out.update({k: tests[k] for k in ("has-tests", "manifest-pr", "manifest-merge", "cluster", "test-module")})
    out["cypress-profiles"] = tests["profiles"]

    out["runner"] = (branch_cfg.get("ci") or {}).get("runner") or DEFAULTS["runner"]
    out["audit-level"] = (branch_cfg.get("audit") or {}).get("level") or DEFAULTS["audit-level"]
    out["max-warnings"] = (branch_cfg.get("lint") or {}).get("max-warnings", DEFAULTS["max-warnings"])
    out["timeout-job"] = tests_cfg.get("timeout-job", DEFAULTS["timeout-job"])
    out["timeout-step"] = tests_cfg.get("timeout-step", DEFAULTS["timeout-step"])
    repo_tests = repo_cfg.get("tests") or {}
    out["testrail-project"] = repo_tests.get("testrail-project", "")
    out["incident-service"] = repo_tests.get("incident-service", "")
    out["maintenance-branches"] = repo_cfg.get("maintenance-branches") or []
    out["default-branch"] = default_branch or ""
    out["release-line"] = bool(ref_name) and (ref_name == default_branch or ref_name in out["maintenance-branches"])
    return out


def to_output_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, dict)):
        return json.dumps(v, separators=(",", ":"))
    return str(v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--ref-name", default=os.environ.get("GITHUB_REF_NAME", ""))
    ap.add_argument("--default-branch", default="")
    ap.add_argument("--default-config", default="", help="path to the .jahia.yml fetched from the default branch")
    ap.add_argument("--image-os", default="resolute")
    ap.add_argument("--output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = ap.parse_args(argv)
    if sys.version_info < (3, 11):
        print("::error::module-metadata needs Python 3.11 or newer (tomllib)")
        return 2
    try:
        out = collect(args.root, args.ref_name, args.default_branch, args.default_config or None, args.image_os)
    except (MetadataError, ET.ParseError, json.JSONDecodeError, tomllib.TOMLDecodeError) as e:
        print(f"::error::module-metadata: {e}")
        return 1
    if args.output:
        with open(args.output, "a", encoding="utf-8") as f:
            for k, v in out.items():
                f.write(f"{k}={to_output_value(v)}\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

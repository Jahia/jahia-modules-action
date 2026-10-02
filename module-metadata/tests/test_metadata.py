"""Rules of the module-metadata reader, on small synthetic checkouts under fixtures/.

Run: python3 -m unittest discover module-metadata/tests
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import metadata  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def collect(name, ref="main", default="main", default_config=None, **kw):
    return metadata.collect(os.path.join(FIX, name), ref, default, default_config, **kw)


class MavenModule(unittest.TestCase):
    def test_single_bundle(self):
        out = collect("synthetic-jdk17")
        self.assertEqual(out["build-tool"], "maven")
        self.assertEqual(out["module-id"], "synthetic-jdk17")
        self.assertEqual(out["parent-version"], "8.2.4.0-SNAPSHOT")
        self.assertEqual(out["java"], "temurin-17.0.2")
        self.assertEqual(out["cache-image"], "ghcr.io/jahia/jahia-docker-mvn-cache:17-jdk-resolute-mvn-loaded")
        self.assertEqual(out["jahia-image"], "ghcr.io/jahia/jahia-ee-dev:8-SNAPSHOT")
        self.assertEqual(out["signature-poms"], ["pom.xml"])
        self.assertFalse(out["has-frontend"])

    def test_image_os_is_an_input(self):
        out = collect("synthetic-jdk17", image_os="noble")
        self.assertTrue(out["cache-image"].endswith(":17-jdk-noble-mvn-loaded"))

    def test_tests_folder(self):
        out = collect("synthetic-jdk17")
        self.assertTrue(out["has-tests"])
        self.assertEqual(out["cypress-profiles"], [])
        self.assertEqual(out["cypress-matrix"], [""])
        self.assertEqual(out["manifest-pr"], "provisioning-manifest-build.yml")
        self.assertEqual(out["manifest-merge"], "provisioning-manifest-snapshot.yml")
        self.assertFalse(out["cluster"])
        self.assertEqual(out["test-module"], "none")

    def test_defaults_without_jahia_yml(self):
        out = collect("synthetic-jdk17")
        self.assertEqual(out["runner"], "ubuntu-latest")
        self.assertEqual(out["audit-level"], "critical")
        self.assertEqual(out["max-warnings"], 1)
        self.assertEqual((out["timeout-job"], out["timeout-step"]), (75, 60))
        self.assertEqual(out["testrail-project"], "")
        self.assertEqual(out["maintenance-branches"], [])

    def test_java_is_required(self):
        with self.assertRaisesRegex(metadata.MetadataError, "declares no java"):
            collect("synthetic-no-java")

    def test_java_major(self):
        for spec, major in (("temurin-8.0.504", 8), ("temurin-17", 17), ("11", 11), ("1.8", 8), ("zulu-21.0.1", 21)):
            self.assertEqual(metadata.java_major(spec), major, spec)


class Reactor(unittest.TestCase):
    def test_several_signed_submodules_need_a_declaration(self):
        with self.assertRaisesRegex(metadata.MetadataError, "several signed submodules \\(synthetic-core, synthetic-ui\\)"):
            collect("synthetic-reactor-ambiguous")

    def test_declared_module_and_signature_in_bundle_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-reactor-ambiguous"), os.path.join(tmp, "r"))
            with open(os.path.join(d, ".jahia.yml"), "w") as f:
                f.write("repository:\n  module: synthetic-ui\n")
            out = metadata.collect(d, "main", "main", None)
            self.assertEqual(out["module-id"], "synthetic-ui")
            self.assertEqual(sorted(out["signature-poms"]), ["core/pom.xml", "test/pom.xml", "ui/pom.xml"])

    def test_declared_module_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-reactor-ambiguous"), os.path.join(tmp, "r"))
            with open(os.path.join(d, ".jahia.yml"), "w") as f:
                f.write("repository:\n  module: nope\n")
            with self.assertRaisesRegex(metadata.MetadataError, "names no submodule"):
                metadata.collect(d, "main", "main", None)

    def test_test_submodule_is_not_a_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-reactor-ambiguous"), os.path.join(tmp, "r"))
            shutil.rmtree(os.path.join(d, "ui"))
            out = metadata.collect(d, "main", "main", None)
            self.assertEqual(out["module-id"], "synthetic-core")


class JavaScriptModule(unittest.TestCase):
    def test_package_json_only(self):
        out = collect("synthetic-js-module")
        self.assertEqual(out["build-tool"], "javascript")
        self.assertEqual(out["module-id"], "synthetic-templates")
        self.assertEqual(out["java"], "")
        self.assertEqual(out["cache-image"], "")
        self.assertEqual(out["node"], "22")
        self.assertTrue(out["has-frontend"])
        self.assertFalse(out["has-js-tests"], "no test script")
        self.assertFalse(out["has-lint"], "no lint script")
        self.assertFalse(out["has-tests"])


class JahiaYml(unittest.TestCase):
    def test_unknown_key_is_refused(self):
        with self.assertRaisesRegex(metadata.MetadataError, "unknown key 'branch.audit.levl'"):
            collect("synthetic-bad-key")

    def test_branch_section_from_checkout_and_repository_section_from_default_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-jdk17"), os.path.join(tmp, "r"))
            with open(os.path.join(d, ".jahia.yml"), "w") as f:
                f.write("repository:\n  maintenance-branches: [stale_x]\nbranch:\n  ci:\n    runner: self-hosted\n  tests:\n    timeout-job: 140\n")
            default_copy = os.path.join(tmp, "default.yml")
            with open(default_copy, "w") as f:
                f.write("repository:\n  maintenance-branches: [3_6_x]\n  tests:\n    testrail-project: Synthetic\n")
            out = metadata.collect(d, "3_6_x", "main", default_copy)
            self.assertEqual(out["runner"], "self-hosted")
            self.assertEqual(out["timeout-job"], 140)
            self.assertEqual(out["maintenance-branches"], ["3_6_x"], "repository: comes from the default branch's copy")
            self.assertEqual(out["testrail-project"], "Synthetic")

    def test_bad_audit_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-jdk17"), os.path.join(tmp, "r"))
            with open(os.path.join(d, ".jahia.yml"), "w") as f:
                f.write("branch:\n  audit:\n    level: severe\n")
            with self.assertRaisesRegex(metadata.MetadataError, "audit.level must be one of"):
                metadata.collect(d, "main", "main", None)

    def test_excluded_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-jdk17"), os.path.join(tmp, "r"))
            for n in ("cypress.config-a.ts", "cypress.config-b.ts", "cypress.config-performance.ts", "cypress.config.common.ts"):
                open(os.path.join(d, "tests", n), "w").close()
            with open(os.path.join(d, ".jahia.yml"), "w") as f:
                f.write("branch:\n  tests:\n    exclude-profiles: [performance]\n")
            out = metadata.collect(d, "main", "main", None)
            self.assertEqual(out["cypress-profiles"], ["cypress.config-a.ts", "cypress.config-b.ts"])
            self.assertEqual(out["cypress-matrix"], out["cypress-profiles"])


class Cluster(unittest.TestCase):
    def test_cluster_is_what_the_default_compose_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-jdk17"), os.path.join(tmp, "r"))
            open(os.path.join(d, "tests", "docker-compose-cluster.yml"), "w").write("services:\n  jahia-browsing-a: {}\n  jahia-browsing-b: {}\n")
            self.assertFalse(metadata.collect(d, "main", "main", None)["cluster"], "a cluster file serves other workflows")
            open(os.path.join(d, "tests", "docker-compose.yml"), "w").write("services:\n  jahia-browsing-a: {}\n  jahia-browsing-b: {}\n  mariadb: {}\n")
            self.assertTrue(metadata.collect(d, "main", "main", None)["cluster"])


class ReleaseLine(unittest.TestCase):
    def test_default_branch_and_listed_maintenance_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = shutil.copytree(os.path.join(FIX, "synthetic-jdk17"), os.path.join(tmp, "r"))
            default_copy = os.path.join(tmp, "default.yml")
            with open(default_copy, "w") as f:
                f.write("repository:\n  maintenance-branches: [2_x, 3_6_x]\n")
            self.assertTrue(metadata.collect(d, "main", "main", default_copy)["release-line"])
            self.assertTrue(metadata.collect(d, "3_6_x", "main", default_copy)["release-line"])
            self.assertFalse(metadata.collect(d, "something_x", "main", default_copy)["release-line"])
            self.assertFalse(metadata.collect(d, "feature/x", "main", default_copy)["release-line"])

    def test_output_values(self):
        self.assertEqual(metadata.to_output_value(True), "true")
        self.assertEqual(metadata.to_output_value(["a", "b"]), '["a","b"]')
        self.assertEqual(metadata.to_output_value(140), "140")


if __name__ == "__main__":
    unittest.main()

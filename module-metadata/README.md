# module-metadata

Reads what a Jahia module repository states about itself and emits it as outputs, so a reusable
workflow derives its jobs instead of asking for inputs.

```yaml
- id: meta
  uses: jahia/jahia-modules-action/module-metadata@v2
- uses: some-step
  with:
    image: ${{ steps.meta.outputs.cache-image }}
```

## Sources, in order of authority

| Output | Read from | Rule |
|---|---|---|
| `build-tool` | root files | `pom.xml` → `maven`, else `package.json` → `javascript` |
| `module-id` | `pom.xml` | the root `artifactId` of a `bundle`; for a `pom` reactor, the one signed submodule outside `test`, `tests`, `samples`, `examples` directories and the `org.jahia.test` and `org.jahia.samples` groups, or `repository.module` in `.jahia.yml` when several qualify |
| `parent-version` | `pom.xml` | version of the `org.jahia.modules:jahia-modules` parent |
| `java`, `node`, `yarn` | `mise.toml` | `java` is required for a Maven module: the JDK is declared, never derived |
| `cache-image` | `java` | `ghcr.io/jahia/jahia-docker-mvn-cache:<major>-jdk-<image-os>-mvn-loaded` |
| `jahia-image` | `parent-version` | `ghcr.io/jahia/jahia-ee-dev:<major>-SNAPSHOT` |
| `signature-poms` | poms | the poms carrying `jahia-module-signature` (property) or `Jahia-Signature` (bundle instruction) |
| `has-frontend` | `pom.xml`, `package.json` | `frontend-maven-plugin`, or a root `package.json` |
| `has-js-tests` | `package.json` | a `test` script; the pull-request workflow runs `yarn test` when true |
| `has-tests`, `cypress-profiles`, `manifest-pr`, `manifest-merge`, `cluster`, `test-module` | `tests/` | a `cypress.config*.ts`; the `cypress.config-*.ts` files minus `branch.tests.exclude-profiles`; `provisioning-manifest-build.yml` and `-snapshot.yml` by exact name; two `jahia-browsing-*` services in `docker-compose.yml` (a `docker-compose-cluster.yml` serves other workflows); `tests/jahia-module/pom.xml` or `package.json` |
| `runner`, `audit-level`, `max-warnings`, `timeout-job`, `timeout-step` | `.jahia.yml` `branch:` | defaults `ubuntu-latest`, `critical`, `1`, `75`, `60` |
| `testrail-project`, `incident-service`, `maintenance-branches` | `.jahia.yml` `repository:` | read from the default branch's copy, whatever branch the run is on |
| `release-line` | context | `true` on the default branch and on a listed maintenance branch |

## `.jahia.yml`

Two sections. `repository:` is read from the **default branch's copy** by every run, so one commit
on the default branch is the whole change and no maintenance branch carries these keys. `branch:`
is read from the branch the run is on, because these values can differ per line. A key that is not
listed below fails the run: a typo must not fall back to a default.

```yaml
repository:
  module: my-module-core           # a reactor with several signed submodules
  maintenance-branches: [3_x, 4_6_x]
  tests:
    testrail-project: My Module
    incident-service: my-module
branch:
  ci:
    runner: self-hosted
  audit:
    level: high                    # low, moderate, high, critical
  lint:
    max-warnings: 8
  tests:
    exclude-profiles: [performance]
    timeout-job: 140
    timeout-step: 90
```

The file is meant to stay small: every key is a difference between repositories, and the goal is to
remove the difference, not to grow the file.

## Running the tests

```bash
python3 -m unittest discover -s module-metadata/tests -v
```

Python 3.11 or newer, with PyYAML.

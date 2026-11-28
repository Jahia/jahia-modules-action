#!/usr/bin/env bash
# Usage: analyze.sh <pom.xml> <output directory>
# Writes third-party.tsv, the licenses of the compile and runtime dependencies of the project,
# and direct.txt, the direct dependencies of each of its modules, which src/report.py compares.
# The check never blocks the pull request: when Maven fails or writes no report, the script
# writes the reason in the file "error", which the comment shows, and exits 0.
set -euo pipefail

POM=$1
OUT=$2
TEMPLATE="$(cd "$(dirname "$0")" && pwd)/third-party.ftl"
MVN=(mvn "-Dmaven.repo.local=${MVN_LOCAL_REPO:-${HOME}/.m2/repository}" -f "${POM}" --no-transfer-progress --batch-mode)
LICENSE_OPTIONS=(-Dlicense.includedScopes=compile,runtime -Dlicense.excludedScopes=test,provided -Dlicense.excludedTypes=war,pom '-Dlicense.excludedGroups=^org\.jahia\..*' -Dlicense.useMissingFile=true)

mkdir -p "${OUT}"
rm -f "${OUT}/third-party.tsv" "${OUT}/direct.txt" "${OUT}/error"

stop() {
  echo "$1" > "${OUT}/error"
  echo "::warning::dependencies-check-java: $1"
  exit 0
}

# The command a developer runs to read the same licenses, in the plugin's own THIRD-PARTY.txt.
# It is written before the first Maven call, so a failure of the head never shows the command
# of the base, and again once the packaging names the goal.
export_command() {
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "LICENSE_COMMAND=mvn -f ${POM} $1 -Dlicense.force=true -Dlicense.includedScopes=compile,runtime -Dlicense.excludedScopes=test,provided -Dlicense.excludedTypes=war,pom -Dlicense.excludedGroups=\"^org\\.jahia\\..*\" -Dlicense.useMissingFile=true" >> "${GITHUB_ENV}"
  fi
}
export_command license:add-third-party

# add-third-party writes one report per module and none for a pom root, and
# aggregate-add-third-party writes the report of the whole reactor but skips any other packaging.
PACKAGING=$("${MVN[@]}" -N help:evaluate -Dexpression=project.packaging -q -DforceStdout) ||
  stop "Maven could not read the packaging of ${POM}."
if [[ "${PACKAGING}" == "pom" ]]; then
  GOAL=license:aggregate-add-third-party
else
  GOAL=license:add-third-party
fi
export_command "${GOAL}"

"${MVN[@]}" "${GOAL}" dependency:list "${LICENSE_OPTIONS[@]}" \
  -Dlicense.force=true \
  "-Dlicense.fileTemplate=${TEMPLATE}" \
  -Dlicense.thirdPartyFilename=third-party.tsv \
  "-Dlicense.outputDirectory=${OUT}" \
  -DexcludeTransitive=true \
  -DincludeScope=runtime \
  "-DoutputFile=${OUT}/direct.txt" \
  -DappendOutput=true ||
  stop "Maven failed on ${POM}."

# A project can skip the license goal in its own POM, and the plugin then writes nothing.
[[ -f "${OUT}/third-party.tsv" ]] ||
  stop "Maven wrote no license report for ${POM}, as when its POM skips the license goal."


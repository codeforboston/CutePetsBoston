#!/usr/bin/env bash
# Regenerate vendor/rescuegroups_client/ from the upstream RescueGroups.org
# OpenAPI spec using openapi-generator-cli via Docker.
#
# Usage:
#   ./scripts/generate_rescuegroups_client.sh
#
# Requires: docker, curl, gh (only for the SHA pin)

set -euo pipefail

GENERATOR_IMAGE="openapitools/openapi-generator-cli:v7.23.0"
SPEC_OWNER="api-evangelist"
SPEC_REPO="rescuegroups-org"
SPEC_PATH="openapi/rescuegroups-org-openapi.yml"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/vendor/rescuegroups_client"
SPEC_FILE="$(mktemp -t openapi-XXXXXX.yml)"
trap 'rm -f "${SPEC_FILE}"' EXIT

# Pin to a specific commit SHA so the build is reproducible.
SHA="$(gh api "repos/${SPEC_OWNER}/${SPEC_REPO}/commits/main" --jq '.sha')"
echo "Pinned spec SHA: ${SHA}"

curl -fsSL \
  "https://raw.githubusercontent.com/${SPEC_OWNER}/${SPEC_REPO}/${SHA}/${SPEC_PATH}" \
  -o "${SPEC_FILE}"

echo "Validating spec..."
docker run --rm \
  -v "${SPEC_FILE}:/spec/openapi.yml:ro" \
  "${GENERATOR_IMAGE}" \
  validate -i /spec/openapi.yml

echo "Generating Python client to ${OUT_DIR}..."
mkdir -p "${REPO_ROOT}/vendor"
rm -rf "${OUT_DIR}"
docker run --rm \
  -v "${REPO_ROOT}/vendor:/local/out" \
  -v "${SPEC_FILE}:/spec/openapi.yml:ro" \
  "${GENERATOR_IMAGE}" generate \
    -i /spec/openapi.yml \
    -g python \
    -o /local/out/rescuegroups_client \
    --additional-properties=packageName=rescuegroups_client,projectName=rescuegroups-client,pythonVersion=3.12 \
    --git-host=github.com --git-user-id=codeforboston --git-repo-id=CutePetsBoston

echo "Tidying non-source artefacts..."
# Keep only the package and the generated docs. Delete everything else
# (CI configs, tests, build outputs, generator metadata, etc.) — they're
# not source and we don't want them in the repo.
rm -rf \
  "${OUT_DIR}/.github" \
  "${OUT_DIR}/.gitlab-ci.yml" \
  "${OUT_DIR}/.openapi-generator" \
  "${OUT_DIR}/.openapi-generator-ignore" \
  "${OUT_DIR}/.pytest_cache" \
  "${OUT_DIR}/.tox" \
  "${OUT_DIR}/.travis.yml" \
  "${OUT_DIR}/build" \
  "${OUT_DIR}/dist" \
  "${OUT_DIR}/git_push.sh" \
  "${OUT_DIR}/pyproject.toml" \
  "${OUT_DIR}/requirements.txt" \
  "${OUT_DIR}/setup.cfg" \
  "${OUT_DIR}/setup.py" \
  "${OUT_DIR}/test" \
  "${OUT_DIR}/test-requirements.txt" \
  "${OUT_DIR}/tox.ini"
find "${OUT_DIR}" -name "*.egg-info" -type d -exec rm -rf {} +
rm -f "${OUT_DIR}/test.egg-info"

cat > "${OUT_DIR}/README.md" <<EOF
# rescuegroups_client — generated

**Do not edit by hand.** Regenerate via:

\`\`\`bash
./scripts/generate_rescuegroups_client.sh
\`\`\`

Generator: openapi-generator-cli v7.23.0
Source: https://github.com/${SPEC_OWNER}/${SPEC_REPO}
Last pinned to spec commit: \`${SHA}\`
EOF

echo "Done."

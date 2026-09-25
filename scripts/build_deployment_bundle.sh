#!/usr/bin/env bash
# Build the OptivEdge deployment bundle: the project template plus every wheel
# (OptivEdge, OptivEdgeIntegrations, OptivEdgeAssessments, and all of their
# public PyPI dependencies) needed to stand up a new engagement offline.
#
# Run this from a machine with PyPI access. The resulting deployment_template/
# directory is fully self-contained and can be copied to an air-gapped target
# with no further network access required.
#
# Usage:
#   ./scripts/build_deployment_bundle.sh
#
# Optional overrides (defaults assume the three repos are sibling directories):
#   OPTIVEDGE_REPO=~/PythonProjects/OptivEdge \
#   OPTIVEDGE_INTEGRATIONS_REPO=~/PythonProjects/OptivEdgeIntegrations \
#   OPTIVEDGE_ASSESSMENTS_REPO=~/PythonProjects/OptivEdgeAssessments \
#   ./scripts/build_deployment_bundle.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPTIVEDGE_REPO="${OPTIVEDGE_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
OPTIVEDGE_INTEGRATIONS_REPO="${OPTIVEDGE_INTEGRATIONS_REPO:-$(cd "$OPTIVEDGE_REPO/../OptivEdgeIntegrations" && pwd)}"
OPTIVEDGE_ASSESSMENTS_REPO="${OPTIVEDGE_ASSESSMENTS_REPO:-$(cd "$OPTIVEDGE_REPO/../OptivEdgeAssessments" && pwd)}"

TEMPLATE_DIR="$OPTIVEDGE_REPO/src/optivedge/deployment_template"
WHEELS_DIR="$TEMPLATE_DIR/wheels"

echo "OptivEdge repo:             $OPTIVEDGE_REPO"
echo "OptivEdgeIntegrations repo: $OPTIVEDGE_INTEGRATIONS_REPO"
echo "OptivEdgeAssessments repo:  $OPTIVEDGE_ASSESSMENTS_REPO"
echo "Wheels output:              $WHEELS_DIR"
echo

if [ ! -d "$OPTIVEDGE_REPO/.venv" ]; then
    echo "error: $OPTIVEDGE_REPO/.venv not found -- set up OptivEdge's venv first" >&2
    exit 1
fi

# shellcheck disable=SC1091
source "$OPTIVEDGE_REPO/.venv/bin/activate"

rm -rf "$WHEELS_DIR"
mkdir -p "$WHEELS_DIR"

# setuptools' build/lib is an accumulator: it copies sources in and never removes files
# that have since been deleted or moved in the source tree. A stale one silently ships
# both the old and new paths of anything reorganised - measured on OptivEdgeIntegrations,
# where a docs/ reshuffle produced a wheel carrying 22 files for 14 real ones. Clear it in
# every repo before building, or the offline bundle inherits the staleness.
for repo in "$OPTIVEDGE_REPO" "$OPTIVEDGE_INTEGRATIONS_REPO" "$OPTIVEDGE_ASSESSMENTS_REPO"; do
    rm -rf "$repo/build"
done

echo "Building wheels for OptivEdge (and its dependencies)..."
pip wheel "$OPTIVEDGE_REPO" -w "$WHEELS_DIR"

echo "Building wheels for OptivEdgeIntegrations (and its dependencies)..."
pip wheel "$OPTIVEDGE_INTEGRATIONS_REPO" -w "$WHEELS_DIR"

echo "Building wheels for OptivEdgeAssessments (and its dependencies)..."
pip wheel "$OPTIVEDGE_ASSESSMENTS_REPO" -w "$WHEELS_DIR"

echo
echo "Bundle ready at: $TEMPLATE_DIR/"
echo "Wheels built:"
ls -1 "$WHEELS_DIR" | grep -v '.gitkeep' | sort

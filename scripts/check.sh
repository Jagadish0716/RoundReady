#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

ruff format --check .
ruff check .
mypy --strict libs/roundready_common scripts/test.py

for service_dir in services/*; do
  if [[ -d "${service_dir}/app" ]]; then
    (
      cd "${service_dir}"
      MYPYPATH="${repo_root}/libs" PYTHONPATH=".:${repo_root}/libs" \
        mypy --strict app tests
    )
    PYTHONPATH="${service_dir}:libs" pytest "${service_dir}/tests"
  fi
done

#!/usr/bin/env bash
set -euo pipefail

ruff format --check .
ruff check .

for service_dir in services/*; do
  if [[ -d "${service_dir}/app" ]]; then
    PYTHONPATH="${service_dir}:libs" mypy "${service_dir}/app"
    PYTHONPATH="${service_dir}:libs" pytest "${service_dir}/tests"
  fi
done

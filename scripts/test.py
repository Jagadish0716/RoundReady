"""Run each microservice test suite in an isolated Python import namespace."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SERVICES = (
    "api-gateway",
    "auth-service",
    "user-service",
    "interviewer-service",
    "booking-service",
    "payment-service",
    "interview-service",
    "notification-service",
)


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    pytest = repository / ".venv" / "bin" / "pytest"
    command = [str(pytest)] if pytest.is_file() else [sys.executable, "-m", "pytest"]

    for service in SERVICES:
        service_dir = repository / "services" / service
        environment = os.environ.copy()
        python_paths = [str(service_dir), str(repository / "libs")]
        if existing := environment.get("PYTHONPATH"):
            python_paths.append(existing)
        environment["PYTHONPATH"] = os.pathsep.join(python_paths)

        print(f"\n==> {service}", flush=True)
        result = subprocess.run(command, cwd=service_dir, env=environment, check=False)
        if result.returncode != 0:
            return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Rotate the local Postgres password: set a new random one in the database, then in .env.postgres.

Usage: python scripts/rotate_db_password.py [--env-file .env.postgres] [--service postgres]
Restart the API and worker afterwards so they pick up the new password.
"""

import argparse
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def write_password(path: Path, password: str):
    """Replace POSTGRES_PASSWORD in place, atomically, keeping every other line and the file's permissions."""
    lines = [f"POSTGRES_PASSWORD={password}" if line.startswith("POSTGRES_PASSWORD=") else line
             for line in path.read_text().splitlines()]
    mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        handle.write("\n".join(lines) + "\n")
    os.chmod(handle.name, mode)
    os.replace(handle.name, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.postgres")
    parser.add_argument("--service", default="postgres", help="the compose service running Postgres")
    args = parser.parse_args()

    env = read_env(args.env_file)
    user, database = env.get("POSTGRES_USER"), env.get("POSTGRES_DB", "postgres")
    if not user:
        print(f"POSTGRES_USER is missing from {args.env_file}.", file=sys.stderr)
        return 1
    password = secrets.token_urlsafe(32)
    # The password travels as a psql variable on stdin, never on a command line.
    done = subprocess.run(
        ["docker", "compose", "exec", "-T", args.service, "psql", "-v", "ON_ERROR_STOP=1",
         "-U", user, "-d", database, "-f", "-"],
        input=f"\\set pw '{password}'\nALTER ROLE \"{user}\" WITH PASSWORD :'pw';\n",
        text=True, capture_output=True, cwd=ROOT, check=False,
    )
    if done.returncode != 0:
        print(f"Postgres refused the change; {args.env_file.name} is unchanged.\n{done.stderr.strip()}", file=sys.stderr)
        return 1
    write_password(args.env_file, password)
    print(f"Rotated the password for {user}. Restart the API and worker (make api, make worker).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

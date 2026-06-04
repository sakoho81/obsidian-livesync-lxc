"""Setup URI generation via Deno."""

from __future__ import annotations

import subprocess
from pathlib import Path

UTILS_DIR = Path(__file__).resolve().parent.parent.parent / "utils"
SETUP_URI_TS = UTILS_DIR / "generate_setupuri.ts"


def _find_deno() -> str | None:
    """Find Deno binary, or return None."""
    for name in ("deno",):
        result = subprocess.run(
            ["which", name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    return None


def generate_setup_uri(
    hostname: str,
    database: str,
    username: str,
    password: str,
    passphrase: str = "",
) -> tuple[str, str]:
    """Generate a setup URI using the bundled Deno script.

    Returns (setup_uri, uri_passphrase).
    """
    deno = _find_deno()
    if deno is None:
        raise RuntimeError(
            "Deno is not installed. Install it: curl -fsSL https://deno.land/install.sh | sh"
        )

    script_path = SETUP_URI_TS if SETUP_URI_TS.exists() else None
    if script_path is None:
        # Fallback to upstream URL
        script_path = "https://raw.githubusercontent.com/vrtmrz/obsidian-livesync/main/utils/flyio/generate_setupuri.ts"

    env = {
        **__import__("os").environ,
        "hostname": hostname,
        "database": database,
        "username": username,
        "password": password,
        "passphrase": passphrase,
    }

    result = subprocess.run(
        [deno, "run", "-A", str(script_path)],
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Setup URI generation failed: {result.stderr}")

    output = result.stdout + result.stderr

    # Parse the Deno output to find the URI and passphrase
    setup_uri = ""
    uri_passphrase = ""
    for line in output.splitlines():
        if line.startswith("obsidian://setuplivesync"):
            setup_uri = line.strip()
        elif "passphrase of Setup-URI is:" in line:
            uri_passphrase = line.split("is:", 1)[1].strip()

    if not setup_uri:
        # The URI might be the last non-empty line
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        for line in reversed(lines):
            if line.startswith("obsidian://"):
                setup_uri = line
                break

    return setup_uri, uri_passphrase

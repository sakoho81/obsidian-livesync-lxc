"""Credentials management with pluggable backends."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Protocol

DEFAULT_CREDS_FILE = Path("/root/.obsidian-livesync-credentials")


class CredentialBackend(Protocol):
    """Pluggable credential storage.

    Implement this protocol to swap storage backends (file, Infisical, keyring, etc).
    """

    def load(self) -> dict[str, str]:
        """Return a dict of credential key-value pairs."""
        ...

    def save(self, values: dict[str, str]) -> None:
        """Persist the given credential values."""
        ...


class FileBackend:
    """File-based credential storage with minimal obfuscation."""

    def __init__(self, path: Path = DEFAULT_CREDS_FILE):
        self.path = path

    def load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        values: dict[str, str] = {}
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if not val:
                continue
            if val.startswith("b64:") and key == "COUCHDB_PASSWORD":
                try:
                    val = base64.b64decode(val[4:]).decode()
                except Exception:
                    pass
            values[key] = val
        return values

    def save(self, values: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        password = values.get("COUCHDB_PASSWORD", "")
        if password:
            encoded = base64.b64encode(password.encode()).decode()
            values = {**values, "COUCHDB_PASSWORD": f"b64:{encoded}"}
        lines = [
            "# Obsidian LiveSync - CouchDB Credentials",
            "# KEEP THIS FILE SECURE!",
        ]
        for k, v in values.items():
            lines.append(f"{k}={v}")
        self.path.write_text("\n".join(lines) + "\n")
        self.path.chmod(0o600)


_backend: CredentialBackend = FileBackend()


def set_backend(backend: CredentialBackend) -> None:
    """Replace the credential backend (e.g. Infisical, keyring)."""
    global _backend
    _backend = backend


class Credentials:
    def __init__(
        self,
        couchdb_user: str = "",
        couchdb_password: str = "",
        database_name: str = "obsidian",
        couchdb_port: int = 5984,
    ):
        self.couchdb_user = couchdb_user
        self.couchdb_password = couchdb_password
        self.database_name = database_name
        self.couchdb_port = couchdb_port

    @property
    def couchdb_url(self) -> str:
        return f"http://127.0.0.1:{self.couchdb_port}"

    @property
    def couchdb_auth_url(self) -> str:
        return f"http://{self.couchdb_user}:{self.couchdb_password}@127.0.0.1:{self.couchdb_port}"

    @classmethod
    def load(cls) -> "Credentials":
        values = _backend.load()
        return cls(
            couchdb_user=values.get("COUCHDB_USER", ""),
            couchdb_password=values.get("COUCHDB_PASSWORD", ""),
            database_name=values.get("DATABASE_NAME", "obsidian"),
            couchdb_port=int(values.get("COUCHDB_PORT", "5984")),
        )

    def save(self) -> None:
        _backend.save({
            "COUCHDB_USER": self.couchdb_user,
            "COUCHDB_PASSWORD": self.couchdb_password,
            "DATABASE_NAME": self.database_name,
            "COUCHDB_PORT": str(self.couchdb_port),
        })

    def get_env_exports(self) -> str:
        return (
            f"export COUCHDB_USER='{self.couchdb_user}'\n"
            f"export COUCHDB_PASSWORD='{self.couchdb_password}'\n"
            f"export DATABASE_NAME='{self.database_name}'\n"
            f"export COUCHDB_PORT='{self.couchdb_port}'\n"
        )

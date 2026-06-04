"""Credentials file management."""

from pathlib import Path
from typing import Optional

CREDS_FILE = Path("/root/.obsidian-livesync-credentials")


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
        """Load credentials from the credentials file."""
        if not CREDS_FILE.exists():
            return cls()
        values: dict[str, str] = {}
        for line in CREDS_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val:
                    values[key] = val
        return cls(
            couchdb_user=values.get("COUCHDB_USER", ""),
            couchdb_password=values.get("COUCHDB_PASSWORD", ""),
            database_name=values.get("DATABASE_NAME", "obsidian"),
            couchdb_port=int(values.get("COUCHDB_PORT", "5984")),
        )

    def save(self) -> None:
        """Write credentials to file."""
        CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "# Obsidian LiveSync - CouchDB Credentials\n"
            "# KEEP THIS FILE SECURE!\n"
            f"COUCHDB_USER={self.couchdb_user}\n"
            f"COUCHDB_PASSWORD={self.couchdb_password}\n"
            f"DATABASE_NAME={self.database_name}\n"
            f"COUCHDB_PORT={self.couchdb_port}\n"
        )
        CREDS_FILE.write_text(content)
        CREDS_FILE.chmod(0o600)

    def get_env_exports(self) -> str:
        """Return shell exports for use in subprocess."""
        return (
            f"export COUCHDB_USER='{self.couchdb_user}'\n"
            f"export COUCHDB_PASSWORD='{self.couchdb_password}'\n"
            f"export DATABASE_NAME='{self.database_name}'\n"
            f"export COUCHDB_PORT='{self.couchdb_port}'\n"
        )

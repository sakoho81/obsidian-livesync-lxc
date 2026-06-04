"""CouchDB operations: install, configure, database management."""

import subprocess
import time

import httpx

from obsidian_livesync.config import Credentials

COUCHDB_PORT = 5984


def _couch_url(creds: Credentials) -> str:
    return f"http://{creds.couchdb_user}:{creds.couchdb_password}@127.0.0.1:{COUCHDB_PORT}"


def generate_install_script(creds: Credentials) -> str:
    """Generate a bash install script for CouchDB."""
    return f"""#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq locales curl apt-transport-https gnupg ca-certificates

sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen
locale-gen en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

. /etc/os-release
if [[ "$ID" == "debian" ]]; then
    REPO_DISTRO="${{VERSION_CODENAME}}"
elif [[ "$ID" == "ubuntu" ]]; then
    REPO_DISTRO="${{VERSION_CODENAME}}"
else
    REPO_DISTRO="focal"
fi

curl -fsSL https://couchdb.apache.org/repo/keys.asc | gpg --dearmor -o /usr/share/keyrings/couchdb-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/couchdb-archive-keyring.gpg] https://apache.jfrog.io/artifactory/couchdb-deb/ $REPO_DISTRO main" > /etc/apt/sources.list.d/couchdb.list

apt-get update -qq

echo "couchdb couchdb/mode select standalone" | debconf-set-selections
echo "couchdb couchdb/mode seen true" | debconf-set-selections
echo "couchdb couchdb/bindaddress string 0.0.0.0" | debconf-set-selections
echo "couchdb couchdb/bindaddress seen true" | debconf-set-selections
echo "couchdb couchdb/cookie string $(openssl rand -hex 32)" | debconf-set-selections
echo "couchdb couchdb/adminpass password {creds.couchdb_password}" | debconf-set-selections
echo "couchdb couchdb/adminpass seen true" | debconf-set-selections
echo "couchdb couchdb/adminpass_again password {creds.couchdb_password}" | debconf-set-selections
echo "couchdb couchdb/adminpass_again seen true" | debconf-set-selections

apt-get install -y couchdb

systemctl enable couchdb
systemctl start couchdb
"""


def wait_for_couchdb(creds: Credentials, timeout: int = 30) -> bool:
    """Wait for CouchDB to be ready. Returns True if ready."""
    url = f"{_couch_url(creds)}/_up"
    for _ in range(timeout):
        try:
            r = httpx.get(url, timeout=5)
            if r.status_code == 200 and "ok" in r.text:
                return True
        except httpx.RequestError:
            pass
        time.sleep(1)
    return False


def configure_livesync(creds: Credentials) -> None:
    """Apply all CouchDB settings required for Obsidian LiveSync."""
    base = f"{_couch_url(creds)}/_node/_local/_config"
    settings = {
        "chttpd": {
            "require_valid_user": "true",
            "enable_cors": "true",
            "max_http_request_size": "4294967296",
        },
        "chttpd_auth": {"require_valid_user": "true"},
        "httpd": {
            "WWW-Authenticate": 'Basic realm="couchdb"',
            "enable_cors": "true",
        },
        "couchdb": {"max_document_size": "50000000"},
        "cors": {
            "credentials": "true",
            "origins": "app://obsidian.md,capacitor://localhost,http://localhost",
        },
    }
    for section, items in settings.items():
        for key, value in items.items():
            httpx.put(
                f"{base}/{section}/{key}",
                content=f'"{value}"',
                timeout=10,
            )


def create_database(creds: Credentials, db_name: str | None = None) -> bool:
    """Create a CouchDB database. Returns True if created (201) or already exists (412)."""
    name = db_name or creds.database_name
    r = httpx.put(
        f"{_couch_url(creds)}/{name}",
        timeout=10,
    )
    return r.status_code in (201, 412)


def list_databases(creds: Credentials) -> list[str]:
    """List all databases on the CouchDB instance."""
    r = httpx.get(f"{_couch_url(creds)}/_all_dbs", timeout=10)
    r.raise_for_status()
    return r.json()


def delete_database(creds: Credentials, db_name: str) -> bool:
    """Delete a CouchDB database. Returns True on success."""
    r = httpx.delete(f"{_couch_url(creds)}/{db_name}", timeout=10)
    return r.status_code == 200


def verify_database(creds: Credentials, db_name: str | None = None) -> bool:
    """Check that a database exists and is accessible."""
    name = db_name or creds.database_name
    try:
        r = httpx.get(f"{_couch_url(creds)}/{name}", timeout=10)
        return r.status_code == 200 and "db_name" in r.text
    except httpx.RequestError:
        return False


def check_config(creds: Credentials) -> dict[str, dict[str, str]]:
    """Dump current CouchDB config."""
    r = httpx.get(
        f"{_couch_url(creds)}/_node/_local/_config",
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_server_ip() -> str:
    """Get the primary IP address of this server."""
    result = subprocess.run(
        ["hostname", "-I"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split()[0]

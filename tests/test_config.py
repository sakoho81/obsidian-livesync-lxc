"""Tests for credentials management."""

from pathlib import Path

from obsidian_livesync.config import (
    Credentials,
    FileBackend,
    set_backend,
)


def test_defaults():
    c = Credentials()
    assert c.couchdb_user == ""
    assert c.couchdb_password == ""
    assert c.database_name == "obsidian"
    assert c.couchdb_port == 5984


def test_custom_values():
    c = Credentials(
        couchdb_user="alice",
        couchdb_password="s3cret",
        database_name="my-vault",
        couchdb_port=9999,
    )
    assert c.couchdb_user == "alice"
    assert c.couchdb_password == "s3cret"
    assert c.database_name == "my-vault"
    assert c.couchdb_port == 9999


def test_couchdb_url():
    c = Credentials()
    assert c.couchdb_url == "http://127.0.0.1:5984"


def test_couchdb_auth_url():
    c = Credentials(couchdb_user="user", couchdb_password="pass")
    assert c.couchdb_auth_url == "http://user:pass@127.0.0.1:5984"


def test_get_env_exports():
    c = Credentials(
        couchdb_user="user",
        couchdb_password="pass",
        database_name="db",
    )
    exports = c.get_env_exports()
    assert "export COUCHDB_USER='user'" in exports
    assert "export COUCHDB_PASSWORD='pass'" in exports
    assert "export DATABASE_NAME='db'" in exports
    assert "export COUCHDB_PORT='5984'" in exports


def test_save_and_load(tmp_path):
    creds_path = tmp_path / ".obsidian-livesync-credentials"
    backend = FileBackend(creds_path)
    set_backend(backend)

    original = Credentials(
        couchdb_user="admin",
        couchdb_password="hunter2",
        database_name="vault",
    )
    original.save()

    assert creds_path.exists()

    loaded = Credentials.load()
    assert loaded.couchdb_user == "admin"
    assert loaded.couchdb_password == "hunter2"
    assert loaded.database_name == "vault"
    assert loaded.couchdb_port == 5984


def test_password_obfuscated_on_disk(tmp_path):
    creds_path = tmp_path / ".obsidian-livesync-credentials"
    backend = FileBackend(creds_path)
    set_backend(backend)

    Credentials(
        couchdb_user="admin",
        couchdb_password="secret123",
        database_name="obsidian",
    ).save()

    raw = creds_path.read_text()
    assert "secret123" not in raw
    assert "b64:" in raw


def test_load_missing_file(tmp_path):
    missing = tmp_path / "nonexistent"
    backend = FileBackend(missing)
    set_backend(backend)

    c = Credentials.load()
    assert c.couchdb_user == ""
    assert c.couchdb_password == ""


def test_load_ignores_comments_and_blanks(tmp_path):
    creds_path = tmp_path / ".obsidian-livesync-credentials"
    creds_path.write_text(
        "# comment line\n"
        "COUCHDB_USER=admin\n"
        "\n"
        "COUCHDB_PASSWORD=b64:dGVzdA==\n"
        "DATABASE_NAME=vault\n"
        "COUCHDB_PORT=5984\n"
    )
    backend = FileBackend(creds_path)
    set_backend(backend)

    loaded = Credentials.load()
    assert loaded.couchdb_user == "admin"
    assert loaded.couchdb_password == "test"
    assert loaded.database_name == "vault"


def test_save_file_permissions(tmp_path):
    creds_path = tmp_path / ".obsidian-livesync-credentials"
    backend = FileBackend(creds_path)
    set_backend(backend)

    Credentials(couchdb_user="u", couchdb_password="p").save()
    assert creds_path.stat().st_mode & 0o777 == 0o600

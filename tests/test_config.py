"""Tests for credentials management."""

import pytest

from obsidian_livesync.config import Credentials


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


def test_save_and_load(monkeypatch, tmp_path):
    creds_path = tmp_path / ".obsidian-livesync-credentials"
    monkeypatch.setattr("obsidian_livesync.config.CREDS_FILE", creds_path)

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


def test_load_missing_file(monkeypatch, tmp_path):
    missing = tmp_path / "nonexistent"
    monkeypatch.setattr("obsidian_livesync.config.CREDS_FILE", missing)
    c = Credentials.load()
    assert c.couchdb_user == ""
    assert c.couchdb_password == ""


def test_load_ignores_comments_and_blanks(monkeypatch, tmp_path):
    creds_path = tmp_path / ".obsidian-livesync-credentials"
    monkeypatch.setattr("obsidian_livesync.config.CREDS_FILE", creds_path)
    creds_path.write_text(
        "# comment line\n"
        "COUCHDB_USER=admin\n"
        "\n"
        "COUCHDB_PASSWORD=test\n"
        "DATABASE_NAME=vault\n"
        "COUCHDB_PORT=5984\n"
    )
    loaded = Credentials.load()
    assert loaded.couchdb_user == "admin"
    assert loaded.couchdb_password == "test"
    assert loaded.database_name == "vault"


def test_save_file_permissions(monkeypatch, tmp_path):
    creds_path = tmp_path / ".obsidian-livesync-credentials"
    monkeypatch.setattr("obsidian_livesync.config.CREDS_FILE", creds_path)
    Credentials(couchdb_user="u", couchdb_password="p").save()
    assert creds_path.stat().st_mode & 0o777 == 0o600

"""Tests for CLI commands."""

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from obsidian_livesync.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "setup-uri" in result.stdout
    assert "db" in result.stdout
    assert "check" in result.stdout


def test_db_help():
    result = runner.invoke(app, ["db", "--help"])
    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "list" in result.stdout
    assert "delete" in result.stdout


def test_create_help():
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "--ct-id" in result.stdout
    assert "--hostname" in result.stdout
    assert "--couchdb-user" in result.stdout


def test_setup_uri_help():
    result = runner.invoke(app, ["setup-uri", "--help"])
    assert result.exit_code == 0
    assert "--hostname" in result.stdout
    assert "--database" in result.stdout


def test_create_requires_proxmox_pass_or_aborts(monkeypatch):
    def fake_prompt(*a, **kw):
        if "Proxmox root password" in str(a):
            raise RuntimeError("no interactivity in CI")
        return ""

    monkeypatch.setattr("typer.prompt", fake_prompt)
    result = runner.invoke(app, ["create", "--proxmox-password", "x"])
    assert result.exit_code == 1


def test_db_create_missing_password_prompts(monkeypatch):
    monkeypatch.setattr(
        "obsidian_livesync.config.CREDS_FILE",
        __import__("pathlib").Path("/nonexistent"),
    )
    prompts = []

    def fake_prompt(*a, **kw):
        prompts.append(a)
        return "test"

    monkeypatch.setattr("typer.prompt", fake_prompt)
    monkeypatch.setattr("obsidian_livesync.cli.create_database", lambda *a, **kw: True)

    result = runner.invoke(app, ["db", "create", "new-db"])
    assert result.exit_code == 0
    assert any("CouchDB username" in str(p) for p in prompts)
    assert any("CouchDB password" in str(p) for p in prompts)


def test_db_list_falls_back_to_prompt(monkeypatch):
    monkeypatch.setattr(
        "obsidian_livesync.config.CREDS_FILE",
        __import__("pathlib").Path("/nonexistent"),
    )
    monkeypatch.setattr(
        "obsidian_livesync.cli.console",
            MagicMock(),
    )

    prompts = []

    def fake_prompt(*a, **kw):
        prompts.append(a)
        return "test"

    monkeypatch.setattr("typer.prompt", fake_prompt)
    monkeypatch.setattr(
        "obsidian_livesync.cli.list_databases",
        lambda creds: ["_replicator", "_users", "obsidian"],
    )

    result = runner.invoke(app, ["db", "list"])
    assert result.exit_code == 0
    assert any("CouchDB username" in str(p) for p in prompts)


def test_db_delete_no_force_aborts(monkeypatch):
    monkeypatch.setattr(
        "obsidian_livesync.config.CREDS_FILE",
        __import__("pathlib").Path("/nonexistent"),
    )
    monkeypatch.setattr(
        "obsidian_livesync.cli.delete_database",
        lambda *a, **kw: True,
    )

    def fake_prompt(*a, **kw):
        return "test"

    monkeypatch.setattr("typer.prompt", fake_prompt)

    result = runner.invoke(app, ["db", "delete", "old-db"])
    assert result.exit_code == 1 or "Aborted" in result.stdout


def test_db_delete_force(monkeypatch):
    monkeypatch.setattr(
        "obsidian_livesync.config.CREDS_FILE",
        __import__("pathlib").Path("/nonexistent"),
    )
    monkeypatch.setattr(
        "obsidian_livesync.cli.delete_database",
        lambda *a, **kw: True,
    )

    def fake_prompt(*a, **kw):
        return "test"

    monkeypatch.setattr("typer.prompt", fake_prompt)

    result = runner.invoke(app, ["db", "delete", "--force", "old-db"])
    assert result.exit_code == 0


def test_check_missing_connection(monkeypatch):
    monkeypatch.setattr(
        "obsidian_livesync.config.CREDS_FILE",
        __import__("pathlib").Path("/nonexistent"),
    )

    def fake_prompt(*a, **kw):
        return "test"

    monkeypatch.setattr("typer.prompt", fake_prompt)

    def fake_check(creds):
        raise Exception("connection refused")

    monkeypatch.setattr("obsidian_livesync.cli.check_config", fake_check)

    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    assert "Cannot connect" in result.stdout

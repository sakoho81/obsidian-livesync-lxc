"""Tests for setup URI generation."""

import subprocess

import pytest

from obsidian_livesync.setup_uri import generate_setup_uri


def test_generate_setup_uri_parses_output(mocker):
    stdout = (
        "\n"
        "Your passphrase of Setup-URI is:  patient-haze\n"
        "This passphrase is never shown again, so please note it in a safe place.\n"
        "obsidian://setuplivesync?settings=%5B%22encrypteddata%22%5D\n"
    )
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=stdout,
        stderr="",
    )

    mocker.patch(
        "obsidian_livesync.setup_uri._find_deno",
        return_value="/usr/bin/deno",
    )

    uri, passphrase = generate_setup_uri(
        hostname="http://localhost:5984",
        database="obsidian",
        username="admin",
        password="pass",
    )

    assert uri == "obsidian://setuplivesync?settings=%5B%22encrypteddata%22%5D"
    assert passphrase == "patient-haze"


def test_generate_setup_uri_no_deno_raises(mocker):
    mocker.patch(
        "obsidian_livesync.setup_uri._find_deno",
        return_value=None,
    )

    with pytest.raises(RuntimeError, match="Deno"):
        generate_setup_uri(
            hostname="http://localhost:5984",
            database="obsidian",
            username="admin",
            password="pass",
        )


def test_generate_setup_uri_failure(mocker):
    mocker.patch(
        "obsidian_livesync.setup_uri._find_deno",
        return_value="/usr/bin/deno",
    )
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="Error: invalid configuration",
    )

    with pytest.raises(RuntimeError, match="Setup URI generation failed"):
        generate_setup_uri(
            hostname="http://localhost:5984",
            database="obsidian",
            username="admin",
            password="pass",
        )


def test_generate_setup_uri_passes_environment(mocker):
    mocker.patch(
        "obsidian_livesync.setup_uri._find_deno",
        return_value="/usr/bin/deno",
    )
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="obsidian://setuplivesync?settings=abc\n",
        stderr="",
    )

    generate_setup_uri(
        hostname="https://example.com:5984",
        database="my-vault",
        username="bob",
        password="s3cret",
        passphrase="my-pass",
    )

    call_env = mock_run.call_args.kwargs["env"]
    assert call_env["hostname"] == "https://example.com:5984"
    assert call_env["database"] == "my-vault"
    assert call_env["username"] == "bob"
    assert call_env["password"] == "s3cret"
    assert call_env["passphrase"] == "my-pass"

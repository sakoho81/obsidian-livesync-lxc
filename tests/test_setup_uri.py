"""Tests for setup URI generation."""

from obsidian_livesync.setup_uri import generate_setup_uri


def test_generate_setup_uri_returns_valid_format():
    uri, passphrase = generate_setup_uri(
        hostname="http://localhost:5984",
        database="obsidian",
        username="admin",
        password="pass",
    )
    assert uri.startswith("obsidian://setuplivesync?settings=%25")
    assert "-" in passphrase


def test_generate_setup_uri_with_custom_passphrase():
    uri, passphrase = generate_setup_uri(
        hostname="http://localhost:5984",
        database="obsidian",
        username="admin",
        password="pass",
        passphrase="my-custom-pass",
    )
    assert uri.startswith("obsidian://setuplivesync?settings=%25")
    assert passphrase == "my-custom-pass"


def test_generate_setup_uri_different_calls_different_outputs():
    uri1, _ = generate_setup_uri(
        hostname="http://localhost:5984",
        database="obsidian",
        username="admin",
        password="pass",
    )
    uri2, _ = generate_setup_uri(
        hostname="http://localhost:5984",
        database="obsidian",
        username="admin",
        password="pass",
    )
    assert uri1 != uri2


def test_generate_setup_uri_vault_with_same_passphrase_same_output():
    """Same passphrase should produce different URIs due to random salt/iv."""
    uri1, p1 = generate_setup_uri(
        hostname="http://localhost:5984",
        database="obsidian",
        username="admin",
        password="pass",
        passphrase="shared-secret",
    )
    uri2, p2 = generate_setup_uri(
        hostname="http://localhost:5984",
        database="obsidian",
        username="admin",
        password="pass",
        passphrase="shared-secret",
    )
    assert p1 == p2 == "shared-secret"
    # Different URIs because salt/iv are random each time
    assert uri1 != uri2


def test_generate_setup_uri_format_contains_percent_prefix():
    uri, _ = generate_setup_uri(
        hostname="http://x:5984",
        database="db",
        username="u",
        password="p",
    )
    # Extract the settings payload
    settings = uri.split("settings=", 1)[1]
    # URL-decode it
    from urllib.parse import unquote

    decoded = unquote(settings)
    # Format: %<hex_iv_32><hex_salt_32><base64>
    assert len(decoded) > 65
    assert decoded[0] == "%"
    # IV hex part (32 chars)
    assert all(c in "0123456789abcdef" for c in decoded[1:33])
    # Salt hex part (32 chars)
    assert all(c in "0123456789abcdef" for c in decoded[33:65])

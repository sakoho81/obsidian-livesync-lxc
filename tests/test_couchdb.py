"""Tests for CouchDB operations."""

import pytest
from pytest_httpx import HTTPXMock

from obsidian_livesync import couchdb as cd
from obsidian_livesync.config import Credentials


@pytest.fixture
def creds():
    return Credentials(
        couchdb_user="admin",
        couchdb_password="pass",
        database_name="obsidian",
    )


def test_generate_install_script_contains_credentials(creds):
    script = cd.generate_install_script(creds)
    assert "adminpass password pass" in script
    assert "adminpass_again password pass" in script


def test_generate_install_script_has_basic_structure(creds):
    script = cd.generate_install_script(creds)
    assert "#!/bin/bash" in script
    assert "apt-get update" in script
    assert "apt-get install -y couchdb" in script
    assert "systemctl enable couchdb" in script
    assert "couchdb.apache.org" in script


def test_wait_for_couchdb_ready(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://admin:pass@127.0.0.1:5984/_up",
        text='{"status":"ok"}',
        status_code=200,
    )
    assert cd.wait_for_couchdb(creds, timeout=1) is True


def test_wait_for_couchdb_timeout(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=503)
    assert cd.wait_for_couchdb(creds, timeout=1) is False


def test_configure_livesync_makes_correct_requests(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response()
    httpx_mock.add_response()
    httpx_mock.add_response()
    httpx_mock.add_response()
    httpx_mock.add_response()
    httpx_mock.add_response()
    httpx_mock.add_response()
    httpx_mock.add_response()
    httpx_mock.add_response()

    cd.configure_livesync(creds)

    requests = httpx_mock.get_requests()
    urls = {str(r.url) for r in requests}
    base = "http://admin:pass@127.0.0.1:5984/_node/_local/_config"
    assert f"{base}/chttpd/require_valid_user" in urls
    assert f"{base}/chttpd/enable_cors" in urls
    assert f"{base}/chttpd/max_http_request_size" in urls
    assert f"{base}/chttpd_auth/require_valid_user" in urls
    assert f"{base}/httpd/WWW-Authenticate" in urls
    assert f"{base}/httpd/enable_cors" in urls
    assert f"{base}/couchdb/max_document_size" in urls
    assert f"{base}/cors/credentials" in urls
    assert f"{base}/cors/origins" in urls
    assert len(requests) == 9


def test_create_database_new(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=201)
    assert cd.create_database(creds) is True


def test_create_database_exists(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=412)
    assert cd.create_database(creds) is True


def test_create_database_custom_name(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=201)
    assert cd.create_database(creds, "work-vault") is True
    req = httpx_mock.get_request()
    assert "work-vault" in str(req.url)


def test_list_databases(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://admin:pass@127.0.0.1:5984/_all_dbs",
        json=["_replicator", "_users", "obsidian", "work-vault"],
    )
    dbs = cd.list_databases(creds)
    assert "obsidian" in dbs
    assert "work-vault" in dbs
    assert len(dbs) == 4


def test_delete_database(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://admin:pass@127.0.0.1:5984/old-db",
        status_code=200,
    )
    assert cd.delete_database(creds, "old-db") is True


def test_verify_database_exists(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://admin:pass@127.0.0.1:5984/obsidian",
        text='{"db_name":"obsidian"}',
        status_code=200,
    )
    assert cd.verify_database(creds) is True


def test_verify_database_missing(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=404)
    assert cd.verify_database(creds) is False


def test_check_config(creds, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://admin:pass@127.0.0.1:5984/_node/_local/_config",
        json={
            "chttpd": {
                "require_valid_user": "true",
                "enable_cors": "true",
            },
            "cors": {"credentials": "true"},
        },
    )
    config = cd.check_config(creds)
    assert config["chttpd"]["require_valid_user"] == "true"
    assert config["chttpd"]["enable_cors"] == "true"
    assert config["cors"]["credentials"] == "true"


def test_get_server_ip(mocker):
    mocker.patch("subprocess.run").return_value.stdout = "192.168.1.100 10.0.0.1\n"
    assert cd.get_server_ip() == "192.168.1.100"

import ipaddress

import pytest
from app.core.errors import UrlSafetyError
from app.services import url_extract as ue


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "192.168.1.10",
        "172.16.0.1",
        "169.254.169.254",
        "0.0.0.0",
        "100.64.0.1",
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:127.0.0.1",
    ],
)
def test_blocked_addresses(address):
    assert ue._is_blocked_ip(ipaddress.ip_address(address)) is True


@pytest.mark.parametrize("address", ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses_allowed(address):
    assert ue._is_blocked_ip(ipaddress.ip_address(address)) is False


def test_resolve_and_validate_blocks_private_resolution(monkeypatch):
    monkeypatch.setattr(
        ue.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 80))]
    )
    with pytest.raises(UrlSafetyError):
        ue.resolve_and_validate("evil.test", 80)


def test_validate_url_rejects_unsupported_scheme(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: ["93.184.216.34"])
    with pytest.raises(UrlSafetyError):
        ue.validate_url("ftp://example.com/file")


def test_validate_url_rejects_embedded_credentials(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: ["93.184.216.34"])
    with pytest.raises(UrlSafetyError):
        ue.validate_url("https://user:pass@example.com/")


def test_validate_url_rejects_unusual_port(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: ["93.184.216.34"])
    with pytest.raises(UrlSafetyError):
        ue.validate_url("http://example.com:8080/")


def test_validate_url_accepts_public_https(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: ["93.184.216.34"])
    assert ue.validate_url("https://example.com/page") == ("https", "example.com", 443)

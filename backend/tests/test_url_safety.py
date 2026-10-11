import ipaddress

import httpx
import pytest
import respx
from app.config import Settings
from app.core.errors import UrlFetchError, UrlSafetyError
from app.services import url_extract as ue

PUBLIC_IP = "93.184.216.34"


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
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with pytest.raises(UrlSafetyError):
        ue.validate_url("ftp://example.com/file")


def test_validate_url_rejects_embedded_credentials(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with pytest.raises(UrlSafetyError):
        ue.validate_url("https://user:pass@example.com/")


def test_validate_url_rejects_unusual_port(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with pytest.raises(UrlSafetyError):
        ue.validate_url("http://example.com:8080/")


def test_validate_url_rejects_missing_host(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with pytest.raises(UrlSafetyError):
        ue.validate_url("http:///just/a/path")


def test_validate_url_accepts_public_https(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    assert ue.validate_url("https://example.com/page") == ("https", "example.com", 443)


@pytest.mark.asyncio
async def test_redirect_to_private_destination_is_blocked(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        address = "127.0.0.1" if host == "evil.test" else PUBLIC_IP
        return [(2, 1, 6, "", (address, port))]

    monkeypatch.setattr(ue.socket, "getaddrinfo", fake_getaddrinfo)
    with respx.mock(assert_all_called=False) as mock:
        mock.get("http://public.test/start").mock(
            return_value=httpx.Response(302, headers={"location": "http://evil.test/"})
        )
        with pytest.raises(UrlSafetyError):
            await ue.fetch_and_extract("http://public.test/start", Settings())


@pytest.mark.asyncio
async def test_redirect_loop_is_rejected(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with respx.mock(assert_all_called=False) as mock:
        mock.get("http://start.test/").mock(
            return_value=httpx.Response(302, headers={"location": "http://start.test/"})
        )
        with pytest.raises(UrlFetchError):
            await ue.fetch_and_extract("http://start.test/", Settings())


@pytest.mark.asyncio
async def test_oversized_response_is_rejected(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    body = ("<html><body>" + "x" * 5000 + "</body></html>").encode()
    with respx.mock(assert_all_called=False) as mock:
        mock.get("http://big.test/").mock(
            return_value=httpx.Response(200, headers={"content-type": "text/html"}, content=body)
        )
        with pytest.raises(UrlFetchError):
            await ue.fetch_and_extract("http://big.test/", Settings(verity_url_max_bytes=1024))


@pytest.mark.asyncio
async def test_unsupported_content_type_is_rejected(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with respx.mock(assert_all_called=False) as mock:
        mock.get("http://docs.test/file").mock(
            return_value=httpx.Response(
                200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.4"
            )
        )
        with pytest.raises(UrlFetchError):
            await ue.fetch_and_extract("http://docs.test/file", Settings())


@pytest.mark.asyncio
async def test_timeout_is_reported_as_fetch_error(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with respx.mock(assert_all_called=False) as mock:
        mock.get("http://slow.test/").mock(side_effect=httpx.ConnectTimeout("timed out"))
        with pytest.raises(UrlFetchError):
            await ue.fetch_and_extract("http://slow.test/", Settings())


@pytest.mark.asyncio
async def test_upstream_error_status_is_reported(monkeypatch):
    monkeypatch.setattr(ue, "resolve_and_validate", lambda host, port: [PUBLIC_IP])
    with respx.mock(assert_all_called=False) as mock:
        mock.get("http://broken.test/").mock(return_value=httpx.Response(503))
        with pytest.raises(UrlFetchError):
            await ue.fetch_and_extract("http://broken.test/", Settings())

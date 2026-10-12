"""SSRF-safe article fetching and extraction.

Security controls:
  * only ``http`` and ``https``; no embedded credentials; ports restricted to 80/443;
  * the hostname is resolved and *every* resolved address is checked against
    private / loopback / link-local / reserved / multicast / unspecified ranges,
    including IPv4-mapped, IPv4-translated, 6to4, teredo and NAT64 IPv6 forms;
  * redirects are followed manually (max 5) and re-validated at every hop;
  * connect + read timeouts, a hard response-size cap, and a content-type allowlist;
  * article text is extracted from the already-fetched HTML by trafilatura -- the
    extractor never makes its own network request.

Residual risk: a DNS name can change its answer between our lookup and the socket
connect (classic DNS-rebinding TOCTOU). We mitigate by validating all answers and
re-validating every hop; we do not claim this is a complete defence.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from ..config import Settings
from ..core.errors import UrlFetchError, UrlSafetyError

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443}
ALLOWED_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5

_EXTRA_BLOCKED_NETWORKS = [
    ipaddress.ip_network("100.64.0.0/10"),   # carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("fd00::/8"),
    # NAT64 prefixes embed an IPv4 destination in an IPv6 address; block them explicitly
    # rather than relying on the stdlib's ``is_reserved`` flag, which is version-dependent.
    ipaddress.ip_network("64:ff9b::/96"),    # NAT64 well-known prefix
    ipaddress.ip_network("64:ff9b:1::/48"),  # NAT64 local-use prefix
]


@dataclass
class FetchedArticle:
    url: str
    title: str | None
    text: str


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return True
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None and _is_blocked_ip(ip.ipv4_mapped):
            return True
        if ip.sixtofour is not None and _is_blocked_ip(ip.sixtofour):
            return True
        if ip.teredo is not None and _is_blocked_ip(ip.teredo[1]):
            return True
    for network in _EXTRA_BLOCKED_NETWORKS:
        if ip.version == network.version and ip in network:
            return True
    return False


def resolve_and_validate(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UrlSafetyError(f"Could not resolve host '{host}'.", details={"host": host}) from exc
    addresses: list[str] = []
    for info in infos:
        raw = info[4][0]
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise UrlSafetyError(
                f"Destination '{host}' resolves to a blocked address.",
                details={"host": host, "address": raw},
            )
        if raw not in addresses:
            addresses.append(raw)
    if not addresses:
        raise UrlSafetyError(f"No usable address for host '{host}'.", details={"host": host})
    return addresses


def validate_url(url: str) -> tuple[str, str, int]:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UrlSafetyError("Only http and https URLs are allowed.")
    if not parts.hostname:
        raise UrlSafetyError("URL must include a host.")
    if parts.username or parts.password:
        raise UrlSafetyError("URLs with embedded credentials are not allowed.")
    port = parts.port or (443 if scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise UrlSafetyError("Only ports 80 and 443 are allowed.")
    resolve_and_validate(parts.hostname, port)
    return scheme, parts.hostname, port


def _decode(body: bytes, encoding: str | None) -> str:
    for candidate in (encoding, "utf-8", "latin-1"):
        if not candidate:
            continue
        try:
            return body.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


def _extract_text(html: str, url: str) -> str:
    text = ""
    try:
        import trafilatura

        text = trafilatura.extract(
            html,
            url=url,
            output_format="txt",
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        ) or ""
    except Exception:  # noqa: BLE001 - fall through to the BS4 fallback
        text = ""
    if not text.strip():
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript", "template"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
        except Exception:  # noqa: BLE001
            text = ""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _extract_title(html: str) -> str | None:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.string:
            return soup.title.string.strip()[:300]
    except Exception:  # noqa: BLE001
        return None
    return None


async def fetch_and_extract(url: str, settings: Settings) -> FetchedArticle:
    current = url.strip()
    headers = {
        "User-Agent": settings.verity_user_agent,
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
    }
    timeout = httpx.Timeout(settings.verity_url_timeout_s)

    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        for _ in range(MAX_REDIRECTS + 1):
            validate_url(current)
            try:
                async with client.stream("GET", current, headers=headers) as response:
                    if response.status_code in REDIRECT_STATUSES:
                        location = response.headers.get("location")
                        if not location:
                            raise UrlFetchError("Redirect response without a Location header.")
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise UrlFetchError(f"Upstream returned HTTP {response.status_code}.")
                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
                        raise UrlFetchError(f"Unsupported content type '{content_type}'.")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > settings.verity_url_max_bytes:
                            raise UrlFetchError("Response exceeded the configured size limit.")
                    final_url = str(response.url)
                    encoding = response.encoding
            except httpx.TimeoutException as exc:
                raise UrlFetchError("The request timed out.") from exc
            except httpx.HTTPError as exc:
                raise UrlFetchError(f"Network error while fetching the URL: {exc}") from exc

            html = _decode(bytes(body), encoding)
            text = _extract_text(html, final_url)
            if not text.strip():
                raise UrlFetchError("Could not extract readable text from the page.")
            return FetchedArticle(url=final_url, title=_extract_title(html), text=text)

    raise UrlFetchError("Too many redirects.")

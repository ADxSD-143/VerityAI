# Security

## Threat model

VerityAI takes untrusted text **and untrusted URLs** from anonymous users. The principal risks
are server-side request forgery (SSRF) via the URL feature, resource exhaustion via large
inputs, and information leakage through errors and logs.

## URL fetching (SSRF controls)

Implemented in `backend/app/services/url_extract.py`.

- Only `http` and `https`; URLs with embedded credentials are rejected; only ports **80 and 443**.
- The hostname is resolved and **every** returned address is checked against private, loopback,
  link-local, reserved, multicast and unspecified ranges, including IPv4-mapped IPv6, 6to4 and
  teredo forms, plus explicit networks (carrier-grade NAT `100.64.0.0/10`, documentation ranges,
  `169.254.0.0/16`).
- Redirects are followed **manually** (max 5) and the scheme/host/address are **re-validated at
  every hop**, so a public host cannot redirect into an internal address.
- Connect + read timeouts and a hard response-size cap (default 3 MB) are enforced while
  streaming.
- Content types are allow-listed (`text/html`, `application/xhtml+xml`, `text/plain`).
- Article text is extracted from the already-fetched HTML (trafilatura, with a BeautifulSoup
  fallback). The extractor never makes its own network request, and URLs embedded in fetched
  pages are never followed.

### Residual risk (stated honestly)

A DNS name can change its answer between our lookup and the socket connect (classic DNS
rebinding TOCTOU). We mitigate by validating *all* resolved addresses and re-validating each
hop; we do **not** claim this is a complete defence. Passing the tests below does not prove
comprehensive security.

## Input limits

- Claim text limit and a claim-count cap (`VERITY_MAX_CLAIMS`, default 5).
- URL response size cap and timeouts.
- Source timeouts; a slow source is recorded as an error rather than blocking the request.

## Secrets

- No secret is required for the core pipeline. `FACTCHECK_API_KEY` (optional) and
  `OPENALEX_MAILTO` are read from the environment / `.env`.
- `.env` is gitignored; `.env.example` documents variable names only.
- Tokens and secret environment values are never logged or echoed. Error responses contain a
  safe message and a stable code — no stack traces, no local paths.

## Logging

The app logs lifecycle events (startup, model warm-up) but not request bodies, so private
input text is not written to logs.

## Rate limiting

The public demo does not implement per-client rate limiting; the free host's platform limits
apply. This is a documented limitation, not a hidden assumption.

## Tests

`backend/tests/test_url_safety.py` covers private/loopback/link-local/metadata addresses,
IPv6 and IPv4-mapped forms, unsupported schemes, embedded credentials, unusual ports, and a
private resolution. `backend/tests/test_api.py` covers the `unsafe_url` error path.

## Reporting

This is a research prototype. Do not treat its output as authoritative; always read the cited
sources.

# Security

## Threat model

VerityAI takes untrusted text and URLs from anonymous users. Principal risks are server-side request
forgery (SSRF), resource exhaustion from large or slow request bodies, repeated expensive model
inference, and information leakage through errors and logs.

## Request limits

The public analysis endpoints /api/analyze and /api/analyze-url have a process-local,
per-socket-client-IP sliding-window limit (default 10 requests per 60 seconds). Requests with
bodies larger than 1,000,000 bytes are rejected with HTTP 413. The body must arrive within 5 seconds
or receives HTTP 408. Each analysis has a 60-second total request budget and returns HTTP 504 if it
expires. /health is exempt so health checks continue to work.

The limiter ignores X-Forwarded-For because that header is client-controlled unless the deployment
explicitly configures a trusted proxy. The quota is process-local, so separate workers have separate
counters; it is a best-effort abuse guard, not a distributed quota system. A proxy that presents the
same peer address for all users can cause users to share a bucket. CPU-bound work already running in
a worker thread may continue after the HTTP timeout; the timeout limits the request lifetime but is
not a hard CPU cancellation mechanism.

## URL fetching (SSRF controls)

Implemented in backend/app/services/url_extract.py.

- Only http and https; URLs with embedded credentials are rejected; only ports 80 and 443.
- The hostname is resolved and every returned address is checked against private, loopback,
  link-local, reserved, multicast and unspecified ranges, including IPv4-mapped IPv6, 6to4 and
  teredo forms, plus explicit networks (carrier-grade NAT 100.64.0.0/10, documentation ranges,
  169.254.0.0/16).
- Redirects are followed manually (max 5) and scheme/host/address are re-validated at every hop.
- Connect + read timeouts and a hard response-size cap (default 3 MB) are enforced while streaming.
- Content types are allow-listed (text/html, application/xhtml+xml, text/plain).
- Article text is extracted from the already-fetched HTML. The extractor makes no network request,
  and URLs embedded in fetched pages are never followed.

### Residual risk

A DNS name can change its answer between lookup and socket connect (DNS-rebinding TOCTOU). We
mitigate by validating all answers and every redirect hop; we do not claim complete defence.
Passing tests does not prove comprehensive security.

## Secrets

No secret is required for the core pipeline. FACTCHECK_API_KEY (optional) and OPENALEX_MAILTO are
read from the environment or .env. The .env file is gitignored; .env.example documents variable
names only. Tokens and secret environment values are never logged or echoed.

## Logging

The app logs lifecycle events but not request bodies, so private input text is not written to logs.

## Tests

backend/tests/test_url_safety.py covers URL safety cases. backend/tests/test_limits.py covers
per-client rate and body-size limits. backend/tests/test_timeouts.py covers the analysis timeout.

## Reporting

This is a research prototype. Do not treat its output as authoritative; always read the cited sources.

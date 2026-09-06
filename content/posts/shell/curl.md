---
title: "curl Troubleshooting Cheatsheet"
date: "2026-09-02T21:55:51+0800"
tags: ["shell", "network", "http", "troubleshooting", "cheatsheet"]
description: "Frequently used curl commands for troubleshooting HTTP, DNS, TLS, latency, proxies, and APIs"
draft: true
---

This is an incident-time cheatsheet, not a complete curl manual. Replace the
example hostnames, addresses, credentials, and filenames before running a
command.

## Troubleshooting Decision Map

Start at the center, choose the failure symptom, and run the command on the
matching branch. Use the table below when you need the parameter details.

{{< inline-svg "images/curl-troubleshooting-mindmap.drawio.svg" "Draw.io curl troubleshooting decision map" >}}

## Quick Command Finder

Each example is a complete one-line command. Replace its example hostname,
address, credentials, or filename with the real troubleshooting target.

| Troubleshooting scenario               | Example                                                                                   | Parameter explanation                                                                                        |
| -------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Check whether an endpoint responds     | `curl -I 'https://example.com/'`                                                          | `-I` sends HEAD and prints response headers only.                                                            |
| Send a JSON POST request               | `curl --json '{"name":"Alice"}' 'https://api.example.com/users'`                          | `--json` sets the body, adds JSON headers, and selects POST. Requires curl 7.82+.                            |
| Send a form POST request               | `curl -d 'username=alice' -d 'active=true' 'https://api.example.com/users'`               | `-d` sends form data and selects POST; repeat it for more fields.                                            |
| Test HTTP Basic authentication         | `curl -u 'alice' 'https://api.example.com/private'`                                       | `-u` supplies the username; omitting the password makes curl prompt for it securely.                         |
| Test Bearer-token authentication       | `curl -H "Authorization: Bearer ${API_TOKEN}" 'https://api.example.com/private'`          | `-H` adds the Authorization header; the token is read from `API_TOKEN`.                                      |
| Print only the HTTP status             | `curl -sS -o /dev/null -w '%{response_code}\n' 'https://example.com/'`                    | `-sS` hides progress but keeps errors; `-o` discards the body; `-w` prints the status.                       |
| Measure total request time             | `curl -sS -o /dev/null -w 'total=%{time_total}s\n' 'https://example.com/'`                | `time_total` is the complete duration; the detailed timing command below splits DNS, connect, TLS, and TTFB. |
| Inspect what curl sent and received    | `curl -v 'https://example.com/'`                                                          | `-v` prints connection details and request/response headers to standard error.                               |
| Test a hostname against a specific IP  | `curl --resolve 'service.example.com:443:10.0.0.12' 'https://service.example.com/health'` | `--resolve` overrides DNS while preserving the hostname for TLS SNI and HTTP.                                |
| Compare IPv4 and IPv6                  | `curl -4 'https://example.com/'` / `curl -6 'https://example.com/'`                       | `-4` permits IPv4 only; `-6` permits IPv6 only.                                                              |
| Inspect a TLS negotiation failure      | `curl -v 'https://example.com/'`                                                          | `-v` shows the certificate, TLS version, cipher, and ALPN negotiation.                                       |
| Test a private CA certificate          | `curl --cacert './internal-ca.pem' 'https://service.example.com/'`                        | `--cacert` verifies the server using the supplied PEM CA bundle.                                             |
| Compare behavior over HTTP/1.1         | `curl --http1.1 'https://example.com/'`                                                   | `--http1.1` forces HTTP/1.1 instead of negotiating HTTP/2 or HTTP/3.                                         |
| Test through an HTTP proxy             | `curl -x 'http://127.0.0.1:8080' 'https://example.com/'`                                  | `-x` routes the request through the specified proxy.                                                         |
| Bypass every configured proxy          | `curl --noproxy '*' 'https://example.com/'`                                               | `--noproxy '*'` bypasses command-line and environment-configured proxies.                                    |
| Make HTTP 4xx/5xx fail                 | `curl --fail-with-body 'https://example.com/missing'`                                     | `--fail-with-body` returns exit code 22 while preserving the error response body.                            |
| Stop a hanging request                 | `curl --connect-timeout 3 --max-time 10 'https://example.com/'`                           | `--connect-timeout` limits connection setup; `--max-time` limits the entire request.                         |
| Check supported protocols and features | `curl --version`                                                                          | Shows curl/libcurl versions, TLS backend, supported protocols, and features.                                 |

## POST Requests

Body options such as `--json`, `--data`, and `--form` automatically select
POST. Adding `-X POST` is normally unnecessary.

### POST JSON

```shell
# --json: Send a JSON body, add Content-Type and Accept headers, and select POST.
# Available in curl 7.82.0 and newer; curl does not validate the JSON itself.
curl --json '{"name":"Alice","active":true}' \
  'https://api.example.com/users'
```

For older curl versions:

```shell
# --data-binary: Send the JSON bytes and automatically select POST.
# -H, --header: Tell the server that the request body contains JSON.
curl --data-binary '{"name":"Alice","active":true}' \
  --header 'Content-Type: application/json' \
  'https://api.example.com/users'
```

### POST Form Data

```shell
# --data-urlencode: Encode and send a form field; repeat it for more fields.
# Supplying a data option automatically selects POST.
curl --data-urlencode 'username=alice' \
  --data-urlencode 'message=hello & goodbye' \
  'https://api.example.com/messages'
```

### POST JSON from a File

```shell
# --json @request.json: Read the JSON body from request.json and select POST.
curl --json '@request.json' \
  'https://api.example.com/users'
```

## Inspect the Response

### Headers Only

```shell
# -I, --head: Send an HTTP HEAD request and print response headers only.
curl --head 'https://example.com/'
```

Some applications do not implement HEAD correctly. Use a normal GET while
discarding its body when you need to test the real GET path:

```shell
# -D -, --dump-header -: Write response headers to standard output.
# -o /dev/null, --output: Discard the response body.
curl --dump-header - \
  --output /dev/null \
  'https://example.com/'
```

### Headers and Body

```shell
# -i, --include: Print response headers before the response body.
curl --include 'https://example.com/'
```

### Status Code Only

```shell
# -sS: Hide the progress meter but retain errors.
# -o /dev/null: Discard the response body.
# -w, --write-out: Print metadata after the transfer.
# response_code: Final HTTP status code after the request.
curl --silent --show-error \
  --output /dev/null \
  --write-out '%{response_code}\n' \
  'https://example.com/'
```

### Save Headers, Body, and Status Separately

```shell
# -D: Save response headers to response.headers.
# -o: Save the response body to response.body.
# -w: Print the final status code; shell redirection saves it to response.status.
curl --dump-header response.headers \
  --output response.body \
  --write-out '%{response_code}\n' \
  'https://example.com/' \
  > response.status
```

## See What Happened on the Wire

### Verbose Request

```shell
# -v, --verbose: Show DNS results, connection details, TLS negotiation, and headers.
# -o /dev/null: Discard the response body so the diagnostics are easier to read.
curl --verbose \
  --output /dev/null \
  'https://example.com/'
```

Verbose prefixes are useful when scanning output:

| Prefix    | Meaning                                  |
| --------- | ---------------------------------------- |
| `*`       | Connection or transfer information       |
| `>`       | Header or protocol data sent by curl     |
| `<`       | Header or protocol data received by curl |
| `{` / `}` | TLS data received / sent                 |

### Full Trace

```shell
# --trace-ascii: Write a detailed readable trace to curl.trace.
# --trace-time: Add timestamps to every trace record.
curl --trace-ascii curl.trace \
  --trace-time \
  'https://example.com/'
```

Traces may contain passwords, tokens, cookies, and bodies. Redact them before
sharing.

## Measure Latency

```shell
# -sS: Hide progress while retaining errors.
# -o /dev/null: Discard the response body.
# remote_ip: Address curl actually connected to.
# http_version: HTTP version selected for the final request.
# response_code: Final HTTP response status.
# time_namelookup: Time until DNS resolution completed.
# time_connect: Time until the transport connection completed.
# time_appconnect: Time until the TLS handshake completed.
# time_starttransfer: Time to first response byte, including server processing.
# time_total: Total request duration.
curl --silent --show-error \
  --output /dev/null \
  --write-out 'ip=%{remote_ip}\nhttp=%{http_version}\nstatus=%{response_code}\ndns=%{time_namelookup}s\nconnect=%{time_connect}s\ntls=%{time_appconnect}s\nttfb=%{time_starttransfer}s\ntotal=%{time_total}s\n' \
  'https://example.com/'
```

Interpret the phases approximately:

| Symptom                                     | Likely area                                                   |
| ------------------------------------------- | ------------------------------------------------------------- |
| High `time_namelookup`                      | DNS resolver or DNS path                                      |
| High `time_connect - time_namelookup`       | Network path, firewall, load balancer, or server accept queue |
| High `time_appconnect - time_connect`       | TLS negotiation, certificate chain, or packet loss            |
| High `time_starttransfer - time_appconnect` | Server processing or upstream dependency                      |
| High `time_total - time_starttransfer`      | Slow or large response body                                   |

## Test DNS and Routing

### Force a Specific IP While Preserving TLS and Hostname

This is usually better than calling an HTTPS IP directly because it preserves
the URL hostname for SNI, certificate verification, and the HTTP `Host` header.

```shell
# --resolve: Map example.com:443 to 203.0.113.10 for this command only.
# The original hostname is still used for TLS and HTTP.
curl --resolve 'example.com:443:203.0.113.10' \
  'https://example.com/health'
```

Compare two backends:

```shell
# First request: Force the hostname to backend A.
curl --resolve 'example.com:443:203.0.113.10' \
  'https://example.com/health'

# Second request: Force the same hostname to backend B.
curl --resolve 'example.com:443:203.0.113.11' \
  'https://example.com/health'
```

### Connect to Another Host or Port

```shell
# --connect-to: Send traffic for api.example.com:443 to backend.internal:8443.
# The original hostname remains visible to TLS and HTTP.
curl --connect-to 'api.example.com:443:backend.internal:8443' \
  'https://api.example.com/health'
```

### Compare IPv4 and IPv6

```shell
# -4, --ipv4: Resolve and connect using IPv4 only.
curl --ipv4 'https://example.com/'

# -6, --ipv6: Resolve and connect using IPv6 only.
curl --ipv6 'https://example.com/'
```

### Use a Specific Local Interface

```shell
# --interface: Bind the outgoing connection to this interface or local address.
curl --interface 'eth0' 'https://example.com/'
```

## Troubleshoot TLS

### Inspect the Handshake

```shell
# -v: Show certificate metadata, ALPN negotiation, and TLS handshake details.
# -o /dev/null: Discard the response body.
curl --verbose \
  --output /dev/null \
  'https://example.com/'
```

### Test an Exact TLS Version

```shell
# --tlsv1.2: Set TLS 1.2 as the minimum acceptable version.
# --tls-max 1.2: Set TLS 1.2 as the maximum, forcing exactly TLS 1.2.
curl --tlsv1.2 \
  --tls-max 1.2 \
  'https://example.com/'
```

`--tlsv1.2` by itself means TLS 1.2 **or newer**.

### Trust a Private Certificate Authority

```shell
# --cacert: Verify the server using this PEM-formatted CA bundle.
curl --cacert './internal-ca.pem' \
  'https://service.internal.example.com/'
```

### Test Mutual TLS

```shell
# --cert: Send this client certificate to the server.
# --key: Use the corresponding private key.
# --cacert: Verify the server using this CA bundle.
curl --cert './client.crt' \
  --key './client.key' \
  --cacert './server-ca.crt' \
  'https://mtls.example.com/health'
```

### Temporarily Bypass Certificate Verification

```shell
# -k, --insecure: Disable certificate-chain and hostname verification.
# Use only to confirm a certificate problem; it permits man-in-the-middle attacks.
curl --insecure 'https://development.example.com/'
```

If `--insecure` changes failure into success, fix the hostname, certificate
chain, trust store, or clock. Do not keep `--insecure` as the solution.

## Compare HTTP Versions

```shell
# --http1.1: Force HTTP/1.1.
curl --http1.1 'https://example.com/'

# --http2: Negotiate HTTP/2; the installed build must support it.
curl --http2 'https://example.com/'

# --http3-only: Require HTTP/3 without falling back; support is build-dependent.
curl --http3-only 'https://example.com/'
```

Use `curl --version` to confirm that the desired protocol appears in the
feature list.

## Reproduce API Requests

### GET with Query Parameters

```shell
# -G, --get: Put data fields in the URL query instead of a POST body.
# --data-urlencode: Percent-encode each query value safely.
curl --get \
  --data-urlencode 'q=distributed systems' \
  --data-urlencode 'page=2' \
  'https://api.example.com/search'
```

### Add Headers

```shell
# -H, --header: Add or replace a request header; repeat for multiple headers.
curl --header 'Accept: application/json' \
  --header 'X-Request-ID: troubleshooting-123' \
  'https://api.example.com/health'
```

### Use Another HTTP Method

```shell
# -X, --request: Use PATCH as the HTTP method.
# --json: Supply a JSON request body and headers.
curl --request PATCH \
  --json '{"active":false}' \
  'https://api.example.com/users/42'

# -X DELETE: Send a DELETE request without a body.
curl --request DELETE \
  'https://api.example.com/users/42'
```

`-X` changes the method name only. It does not automatically configure a body
or headers.

### Authentication

```shell
# -u, --user: Use HTTP Basic authentication and prompt for the password.
curl --user 'alice' \
  'https://api.example.com/private'

# -H: Add an OAuth 2.0 Bearer token from an environment variable.
curl --header "Authorization: Bearer ${API_TOKEN}" \
  'https://api.example.com/private'
```

### Cookies

```shell
# -c, --cookie-jar: Save received cookies after the login request.
curl --cookie-jar cookies.txt \
  --data 'username=alice&password=secret' \
  'https://example.com/login'

# -b, --cookie: Load and send cookies from cookies.txt.
curl --cookie cookies.txt \
  'https://example.com/account'
```

## Timeouts, Failures, and Retries

### Bound Every Request

```shell
# --connect-timeout: Allow at most 3 seconds for connection establishment.
# --max-time: Allow at most 10 seconds for the complete operation.
curl --connect-timeout 3 \
  --max-time 10 \
  'https://example.com/health'
```

### Make HTTP Errors Fail

```shell
# --fail-with-body: Return exit code 22 for HTTP 4xx/5xx and keep the error body.
# -sS: Hide progress but keep curl error messages.
curl --fail-with-body \
  --silent \
  --show-error \
  'https://example.com/health'
```

Without `--fail` or `--fail-with-body`, an HTTP 404 or 500 normally still
produces curl exit code `0` because the HTTP transfer itself succeeded.

### Retry Transient Failures

```shell
# --retry 3: Retry transient failures up to 3 times.
# --retry-connrefused: Also retry a refused TCP connection.
# --retry-max-time 30: Limit total time spent retrying to 30 seconds.
# --max-time 10: Limit each individual attempt to 10 seconds.
curl --retry 3 \
  --retry-connrefused \
  --retry-max-time 30 \
  --max-time 10 \
  'https://example.com/health'
```

Retry GET, HEAD, and other idempotent operations. Retrying a POST may repeat a
side effect unless the API supports idempotency keys.

### Detect a Stalled Transfer

```shell
# --speed-limit: Consider the transfer too slow below 1,024 bytes per second.
# --speed-time: Abort only after the low speed persists for 30 seconds.
curl --speed-limit 1024 \
  --speed-time 30 \
  'https://example.com/large-file'
```

## Test Through or Around a Proxy

```shell
# -x, --proxy: Route the request through this HTTP proxy.
curl --proxy 'http://proxy.example.com:8080' \
  'https://example.com/'

# --noproxy '*': Bypass every proxy, including proxy environment variables.
curl --noproxy '*' \
  'https://example.com/'

# --socks5-hostname: Use SOCKS5 and let the proxy resolve the destination name.
curl --socks5-hostname '127.0.0.1:1080' \
  'https://example.com/'
```

curl also reads `http_proxy`, `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY`.
The `http_proxy` variable is intentionally lowercase-only.

## Download and Upload

```shell
# -f: Fail instead of saving an HTTP error page as the requested file.
# -L: Follow redirects.
# -O: Save the file under the final path component from its URL.
# --remove-on-error: Delete an incomplete output file after failure.
curl --fail \
  --location \
  --remote-name \
  --remove-on-error \
  'https://example.com/release.tar.gz'

# -C -: Resume from the size of the existing local file.
# -O: Save to the URL-derived filename.
curl --continue-at - \
  --remote-name \
  'https://example.com/large.iso'

# -T, --upload-file: Upload the local file; HTTP uses PUT.
curl --upload-file './report.json' \
  'https://uploads.example.com/report.json'

# -F, --form: Send a browser-style multipart file upload.
curl --form 'file=@report.json;type=application/json' \
  'https://api.example.com/upload'
```

## Common Exit Codes

|        Code | Meaning                         | First thing to check                                 |
| ----------: | ------------------------------- | ---------------------------------------------------- |
|         `0` | Transfer succeeded              | Add `--fail-with-body` if HTTP errors should fail    |
|         `3` | Malformed URL                   | URL spelling and quoting                             |
|         `5` | Could not resolve proxy         | Proxy hostname and proxy environment                 |
|         `6` | Could not resolve host          | DNS, search domains, and hostname                    |
|         `7` | Failed to connect               | Address, port, firewall, listener, and routing       |
| `16` / `92` | HTTP/2 error                    | Compare with `--http1.1`                             |
|        `22` | HTTP 4xx/5xx with a fail option | Response status and error body                       |
|        `28` | Timeout                         | Timing output, network path, and server latency      |
|        `35` | TLS handshake failed            | TLS version, cipher support, SNI, and verbose output |
|        `47` | Too many redirects              | `Location` chain and redirect loop                   |
|        `52` | Empty server response           | Server/proxy closed without an HTTP response         |
| `55` / `56` | Send/receive failure            | Packet loss, resets, proxy, and load balancer        |
|        `60` | Certificate verification failed | Hostname, trust chain, CA bundle, and system clock   |
|        `67` | Authentication rejected         | Username, password/token, and auth scheme            |
| `95` / `96` | HTTP/3 or QUIC error            | Compare with `--http2` or `--http1.1`                |

Print the installed version's full list with `curl --manual`.

## Troubleshooting Sequence

When the cause is unclear, work through these checks in order:

1. Choose the closest scenario from the **Quick Command Finder** and record its output and exit code.
2. Add `--verbose` to identify whether failure occurs at DNS, connect, TLS, or HTTP.
3. Print the timing breakdown to locate the slow phase.
4. Compare `--ipv4` and `--ipv6`.
5. Use `--resolve` to separate DNS/load-balancer behavior from backend behavior.
6. Compare `--http1.1` and `--http2`.
7. Bypass the proxy with `--noproxy '*'`, or reproduce through the expected proxy.
8. Save headers and body separately so the evidence can be compared or shared.

## References

- [curl command-line man page](https://curl.se/docs/manpage.html)
- [Everything curl: command line](https://everything.curl.dev/cmdline/index.html)
- [Everything curl: verbose operations](https://everything.curl.dev/usingcurl/verbose/index.html)
- [Everything curl: exit codes](https://everything.curl.dev/cmdline/exitcode.html)

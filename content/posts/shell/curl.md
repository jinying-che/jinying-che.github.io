---
title: "curl Troubleshooting Cheatsheet"
date: "2026-09-02T21:55:51+0800"
tags: ["shell", "network", "http", "troubleshooting", "cheatsheet"]
description: "Frequently used curl commands for troubleshooting HTTP, DNS, TLS, latency, proxies, and APIs"
---

Examples use `example.com` and documentation IPs; swap in your target.

{{< rawhtml >}}
<div class="table-scroll" role="region" aria-label="curl cheatsheet" tabindex="0">
<table class="curl-cheatsheet">
  <thead>
    <tr><th>Symptom</th><th>Goal</th><th>Command</th><th>Key details</th></tr>
  </thead>
  <tbody>
    <tr>
      <td class="symptom" rowspan="5">First look</td>
      <td>Headers only</td>
      <td><code>curl -I https://example.com/</code></td>
      <td>HEAD request; some apps mishandle HEAD, so use <code>-sS -D - -o /dev/null</code> to test the real GET</td>
    </tr>
    <tr>
      <td>See the wire</td>
      <td><code>curl -v -o /dev/null https://example.com/</code></td>
      <td><code>*</code> info, <code>&gt;</code> sent, <code>&lt;</code> received; output goes to stderr</td>
    </tr>
    <tr>
      <td>Status only</td>
      <td><code>curl -sS -o /dev/null -w '%{response_code}\n' https://example.com/</code></td>
      <td><code>-sS</code> hides progress but keeps errors</td>
    </tr>
    <tr>
      <td>Readable JSON body</td>
      <td><code>curl -sS https://api.example.com/users/42 | jq .</code></td>
      <td><code>-sS</code> keeps the progress meter out of the pipe</td>
    </tr>
    <tr>
      <td>Follow redirects</td>
      <td><code>curl -L http://example.com/</code></td>
      <td>Exit <code>47</code> = too many redirects</td>
    </tr>
    <tr>
      <td class="symptom" rowspan="3">Connection</td>
      <td>Is the port open?</td>
      <td><code>curl -v telnet://db.example.com:5432</code></td>
      <td>"Connected to" = TCP is reachable; no nc or telnet needed. Exit <code>7</code> = connect failed</td>
    </tr>
    <tr>
      <td>Which backend answered?</td>
      <td><code>curl -sS -o /dev/null -w '%{remote_ip}:%{remote_port} %{response_code}\n' https://example.com/</code></td>
      <td>Shows where a load balancer, DNS round-robin, or VIP sent you</td>
    </tr>
    <tr>
      <td>Bound the request</td>
      <td><code>curl --connect-timeout 3 --max-time 10 https://example.com/</code></td>
      <td><code>--connect-timeout</code> limits connection setup; <code>--max-time</code> the whole request. Exit <code>28</code> = timeout</td>
    </tr>
    <tr>
      <td class="symptom" rowspan="2">Slow / flapping</td>
      <td>Phase timing</td>
      <td><code>curl -sS -o /dev/null -w 'dns=%{time_namelookup} conn=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' https://example.com/</code></td>
      <td>Cumulative times: high dns &rarr; resolver; conn&minus;dns &rarr; network/firewall; tls&minus;conn &rarr; handshake; ttfb&minus;tls &rarr; server</td>
    </tr>
    <tr>
      <td>Watch over time</td>
      <td><code>while true; do curl -sS -o /dev/null -w '%{response_code} %{time_total}\n' https://example.com/health; sleep 1; done</code></td>
      <td>Catches rollouts, intermittent 5xx, and failovers</td>
    </tr>
    <tr>
      <td class="symptom" rowspan="4">DNS / routing</td>
      <td>Pin host to IP</td>
      <td><code>curl --resolve 'example.com:443:203.0.113.10' https://example.com/health</code></td>
      <td>Keeps SNI, cert check, and <code>Host</code>; exit <code>6</code> = DNS failed</td>
    </tr>
    <tr>
      <td>Send to another backend</td>
      <td><code>curl --connect-to 'example.com:443:backend.internal:8443' https://example.com/health</code></td>
      <td>Like <code>--resolve</code>, but can also change the port</td>
    </tr>
    <tr>
      <td>Hit an IP with a Host header</td>
      <td><code>curl -H 'Host: example.com' http://203.0.113.10/</code></td>
      <td>Plain-HTTP virtual-host test; for HTTPS use <code>--resolve</code> so SNI matches</td>
    </tr>
    <tr>
      <td>IPv4 vs IPv6</td>
      <td><code>curl -4 https://example.com/</code> / <code>curl -6 https://example.com/</code></td>
      <td>Isolates a broken address family</td>
    </tr>
    <tr>
      <td class="symptom" rowspan="5">TLS</td>
      <td>Cert subject / expiry</td>
      <td><code>curl -sv -o /dev/null https://example.com/ 2&gt;&amp;1 | grep -E 'subject:|issuer:|expire date:'</code></td>
      <td>Exit <code>60</code> = cert verification failed; exit <code>35</code> = handshake failed</td>
    </tr>
    <tr>
      <td>Private CA</td>
      <td><code>curl --cacert ./internal-ca.pem https://service.internal/</code></td>
      <td>Verifies the server with this PEM CA bundle</td>
    </tr>
    <tr>
      <td>Mutual TLS</td>
      <td><code>curl --cert ./client.crt --key ./client.key --cacert ./ca.pem https://mtls.example.com/health</code></td>
      <td>Sends a client certificate</td>
    </tr>
    <tr>
      <td>Exact TLS version</td>
      <td><code>curl --tlsv1.2 --tls-max 1.2 https://example.com/</code></td>
      <td><code>--tlsv1.2</code> alone means 1.2 <strong>or newer</strong></td>
    </tr>
    <tr>
      <td>Confirm a cert issue</td>
      <td><code>curl -k https://dev.example.com/</code></td>
      <td>Diagnosis only, never the fix</td>
    </tr>
    <tr>
      <td class="symptom">HTTP version</td>
      <td>Compare</td>
      <td><code>curl --http1.1 https://example.com/</code> / <code>curl --http2 https://example.com/</code></td>
      <td>Exit <code>16</code> / <code>92</code> = HTTP/2 error</td>
    </tr>
    <tr>
      <td class="symptom" rowspan="3">Proxy</td>
      <td>Through a proxy</td>
      <td><code>curl -x http://proxy.example.com:8080 https://example.com/</code></td>
      <td>Also reads <code>http_proxy</code>, <code>HTTPS_PROXY</code>, <code>NO_PROXY</code></td>
    </tr>
    <tr>
      <td>Bypass all proxies</td>
      <td><code>curl --noproxy '*' https://example.com/</code></td>
      <td>Overrides the env vars</td>
    </tr>
    <tr>
      <td>SOCKS / SSH tunnel</td>
      <td><code>curl --socks5-hostname 127.0.0.1:1080 https://internal.example.com/</code></td>
      <td>The proxy resolves the hostname, e.g. through <code>ssh -D 1080 jumphost</code></td>
    </tr>
    <tr>
      <td class="symptom">Local / container</td>
      <td>Unix socket</td>
      <td><code>curl --unix-socket /var/run/docker.sock http://localhost/version</code></td>
      <td>For Docker, containerd, and local daemons</td>
    </tr>
    <tr>
      <td class="symptom" rowspan="9">API request</td>
      <td>Reproduce a browser request</td>
      <td>DevTools &rarr; Network &rarr; right-click &rarr; <strong>Copy as cURL</strong></td>
      <td>Exact headers, cookies, and body; strip secrets before sharing</td>
    </tr>
    <tr>
      <td>Any method, JSON body</td>
      <td><code>curl -X PATCH --json '{"name":"Alice","active":true}' https://api.example.com/users/42</code></td>
      <td><code>-X</code> sets the method name only (<code>PUT</code>, <code>PATCH</code>, &hellip;); without it a body means POST. <code>--json</code> adds the body plus <code>Content-Type</code>/<code>Accept</code> headers (curl 7.82+). Use <code>-I</code>, not <code>-X HEAD</code>, which hangs</td>
    </tr>
    <tr>
      <td>Any method, form body</td>
      <td><code>curl -X PUT --data-urlencode 'name=Alice' --data-urlencode 'note=hello &amp; bye' https://api.example.com/users/42</code></td>
      <td>URL-encodes each field; <code>Content-Type: application/x-www-form-urlencoded</code></td>
    </tr>
    <tr>
      <td>GET with query</td>
      <td><code>curl -G --data-urlencode 'q=distributed systems' --data-urlencode 'page=2' https://api.example.com/search</code></td>
      <td><code>-G</code> moves the data into the query string</td>
    </tr>
    <tr>
      <td>Delete</td>
      <td><code>curl -X DELETE https://api.example.com/users/42</code></td>
      <td>No body needed</td>
    </tr>
    <tr>
      <td>Basic auth</td>
      <td><code>curl -u alice https://api.example.com/private</code></td>
      <td>Prompts for the password; exit <code>67</code> = auth rejected</td>
    </tr>
    <tr>
      <td>Bearer token</td>
      <td><code>curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com/private</code></td>
      <td>Token comes from an env var, not the command history</td>
    </tr>
    <tr>
      <td>CORS preflight</td>
      <td><code>curl -i -X OPTIONS -H 'Origin: https://app.example.com' -H 'Access-Control-Request-Method: POST' https://api.example.com/users</code></td>
      <td>Check the <code>Access-Control-Allow-*</code> response headers</td>
    </tr>
    <tr>
      <td>Fail on 4xx/5xx</td>
      <td><code>curl --fail-with-body https://example.com/missing</code></td>
      <td>curl 7.76+. Without it, a 404 or 500 still exits <code>0</code>; with it, exit <code>22</code></td>
    </tr>
    <tr>
      <td class="symptom">Feature missing</td>
      <td>Check build</td>
      <td><code>curl --version</code></td>
      <td>Lists protocols, TLS backend, and features</td>
    </tr>
  </tbody>
</table>
</div>
{{< /rawhtml >}}

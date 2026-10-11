"""A local reverse proxy for the Kubeflow Pipelines UI on a cluster whose Kubeflow front door (Istio,
oauth2-proxy, the central dashboard) is not running: it adds the user header the front door would,
and the profile namespace the dashboard would pick, to each request.

    kubectl -n kubeflow port-forward svc/ml-pipeline-ui 18300:80 &
    python3 ui_proxy.py            # then open http://127.0.0.1:18399/#/runs

For a lab only: anyone who can reach the proxy acts as USER.
"""
import http.client, http.server, re, socketserver, urllib.parse

UPSTREAM, USER, NS = ("localhost", 18300), "user@example.com", "kubeflow-user-example-com"
# outside the central dashboard the UI has no namespace; list calls in multi-user mode need one
LISTS = re.compile(r"^/(?:pipeline/)?apis/v2beta1/(runs|experiments|pipelines|recurringruns)/?$")


def with_namespace(path):
    u = urllib.parse.urlsplit(path)
    if not LISTS.match(u.path):
        return path
    q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
    if q.get("namespace", [""])[0]:
        return path
    q["namespace"] = [NS]
    return urllib.parse.urlunsplit(u._replace(query=urllib.parse.urlencode(q, doseq=True)))

class Proxy(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def _go(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) or None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection", "kubeflow-userid")}
        headers["kubeflow-userid"] = USER
        c = http.client.HTTPConnection(*UPSTREAM, timeout=300)
        try:
            c.request(self.command, with_namespace(self.path), body, headers)
            r = c.getresponse()
            data = r.read()
        except Exception as e:
            self.send_error(502, str(e)); return
        self.send_response(r.status, r.reason)
        for k, v in r.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = _go
    def log_message(self, *a):
        pass

class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

Server(("127.0.0.1", 18399), Proxy).serve_forever()

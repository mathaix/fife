# Runs INSIDE the sandbox (demo 04).
import platform
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

started = time.time()
hits = 0


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global hits
        hits += 1
        body = (
            "<body style='font:2rem system-ui;padding:3rem'>"
            "<h1>Hello from a Modal Sandbox</h1>"
            f"<p>host: <code>{platform.node()}</code></p>"
            f"<p>uptime: {time.time() - started:.0f}s · requests: {hits}</p></body>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

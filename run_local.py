#!/usr/bin/env python3
"""Local dev server — simulates API Gateway → Lambda.
Usage: python run_local.py [port]
Default port: 8000
"""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
load_dotenv()

from lambda_function import handler as lambda_handler


class _Handler(BaseHTTPRequestHandler):

    def _serve(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        query = {}
        for k, vals in parse_qs(parsed.query).items():
            query[k] = vals[0]

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode("utf-8") if length else "{}"

        event = {
            "httpMethod":            self.command,
            "path":                  path,
            "queryStringParameters": query or None,
            "body":                  body,
            "headers":               dict(self.headers),
        }

        result = lambda_handler(event, None)

        self.send_response(result["statusCode"])
        for k, v in result.get("headers", {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(result["body"].encode("utf-8"))

    def do_GET(self):    self._serve()
    def do_POST(self):   self._serve()
    def do_PATCH(self):  self._serve()
    def do_DELETE(self): self._serve()
    def do_OPTIONS(self): self._serve()

    def log_message(self, fmt, *args):
        print(f"  {args[0]} {args[1]}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"GVMC API → http://localhost:{port}")
    print("Test: curl http://localhost:8000/api/wards")
    HTTPServer(("", port), _Handler).serve_forever()

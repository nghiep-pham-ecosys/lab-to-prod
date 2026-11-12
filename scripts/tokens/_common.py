"""Helpers for the token scripts. Standard library only, so they run with plain python3.

Rules these scripts follow:
- a token is never printed, logged or written to the repository;
- it goes from the platform straight into GitHub Secrets through `gh secret set`, on stdin
  (not as a command-line argument, which other processes could read);
- everything you type that is secret is read with getpass, so it does not echo.
"""
from __future__ import annotations

import getpass
import http.server
import json
import secrets as pysecrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

DEFAULT_REPO = "nghiep-pham-ecosys/lab-to-prod"


class TokenError(Exception):
    pass


def ask(label: str, secret: bool = False) -> str:
    value = (getpass.getpass(f"{label}: ") if secret else input(f"{label}: ")).strip()
    if not value:
        raise TokenError(f"{label} is required")
    return value


def http_json(url: str, data: dict | None = None, headers: dict | None = None) -> dict:
    """GET, or POST a form when data is given. Errors never include the request body or URL query."""
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise TokenError(f"{url.split('?')[0]} answered HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise TokenError(f"cannot reach {url.split('?')[0]}: {exc.reason}") from None


def wait_for_code(port: int, state: str, path: str = "/callback") -> str:
    """Serve one request on localhost and return the OAuth code from it."""
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if parsed.path != path:
                self.send_response(404)
                self.end_headers()
                return
            result.update({k: v[0] for k, v in params.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h2>Done. You can close this tab and go back to the terminal.</h2>")

        def log_message(self, *args):  # keep the code out of the terminal
            pass

    with http.server.HTTPServer(("127.0.0.1", port), Handler) as server:
        server.timeout = 300
        while not result:
            server.handle_request()
            if not result:
                raise TokenError("no answer from the browser within 5 minutes")
    if result.get("error"):
        raise TokenError(f"the platform refused: {result.get('error')} {result.get('error_description', '')}")
    if result.get("state") != state:
        raise TokenError("state mismatch: the answer did not come from the sign-in this script started")
    if not result.get("code"):
        raise TokenError("the browser came back without a code")
    return result["code"]


def authorize(auth_url: str, params: dict, port: int, path: str = "/callback") -> tuple[str, str]:
    """Open the browser for sign-in. Returns (code, redirect_uri)."""
    state = pysecrets.token_urlsafe(24)
    redirect = f"http://localhost:{port}{path}"
    url = f"{auth_url}?{urllib.parse.urlencode({**params, 'redirect_uri': redirect, 'state': state})}"
    print("Opening your browser to sign in. If it does not open, copy this address into it:")
    print(f"  {url}")
    webbrowser.open(url)
    return wait_for_code(port, state, path), redirect


def store_secret(name: str, value: str, repo: str = DEFAULT_REPO, kind: str = "secret", run=subprocess.run) -> None:
    """Put a value into GitHub Secrets (or Variables) through gh, on stdin. Never prints the value."""
    if not value:
        raise TokenError(f"{name}: empty value, nothing stored")
    try:
        proc = run(["gh", kind, "set", name, "--repo", repo], input=value, text=True, capture_output=True)
    except FileNotFoundError:
        raise TokenError("the GitHub CLI (gh) is not installed; install it and run `gh auth login`") from None
    if proc.returncode != 0:
        raise TokenError(f"gh could not store {name}: {proc.stderr.strip()[:200]}")
    print(f"  stored {kind} {name} in {repo}")


def main_guard(fn) -> None:
    try:
        fn()
    except TokenError as exc:
        print(f"\nStopped: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)

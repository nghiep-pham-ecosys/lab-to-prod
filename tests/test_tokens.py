import io
import sys
import threading
import time
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tokens"))
import _common as common  # noqa: E402
import facebook_token  # noqa: E402
import linkedin_token  # noqa: E402
import simple_secrets  # noqa: E402
import youtube_token  # noqa: E402

SECRETS = {"client-secret-XYZ", "ACCESS-TOKEN-123", "REFRESH-TOKEN-456", "PAGE-TOKEN-789", "USER-LONG-TOKEN", "999:BOT-TOKEN", "DEV-KEY-000"}


class Recorder:
    def __init__(self):
        self.stored = {}

    def store(self, name, value, repo, kind="secret"):
        self.stored[name] = (value, kind)


def run_flow(fn, answers, responses):
    answers = iter(answers)
    rec = Recorder()
    def http(url, data=None, headers=None):
        for needle, resp in responses:
            if needle in url:
                return resp
        raise AssertionError(url)
    out = io.StringIO()
    kwargs = {"ask": lambda label, secret=False: next(answers), "http_json": http, "store": rec.store}
    if fn not in (simple_secrets.telegram, simple_secrets.devto):
        kwargs["authorize"] = lambda url, params, port, path="/callback": ("the-code", f"http://localhost:{port}/callback")
    with redirect_stdout(out), redirect_stderr(out):
        fn("o/r", **kwargs)
    printed = out.getvalue()
    assert not any(s in printed for s in SECRETS), "a secret was printed"
    return rec.stored, printed


def test_linkedin_stores_token_urn_and_issue_date_without_printing():
    stored, printed = run_flow(linkedin_token.run, ["cid", "client-secret-XYZ"], [
        ("accessToken", {"access_token": "ACCESS-TOKEN-123", "expires_in": 5184000}),
        ("userinfo", {"sub": "AbC9", "name": "N P"})])
    assert stored["LINKEDIN_ACCESS_TOKEN"] == ("ACCESS-TOKEN-123", "secret")
    assert stored["LINKEDIN_PERSON_URN"][0] == "urn:li:person:AbC9"
    assert stored["LINKEDIN_TOKEN_ISSUED"][1] == "variable" and "60 days" in printed


def test_facebook_exchanges_for_a_long_lived_page_token():
    stored, _ = run_flow(facebook_token.run, ["app", "client-secret-XYZ"], [
        ("oauth/access_token", {"access_token": "USER-LONG-TOKEN"}),
        ("me/accounts", {"data": [{"id": "42", "name": "My Page", "access_token": "PAGE-TOKEN-789", "tasks": ["CREATE_CONTENT"]}]})])
    assert stored == {"FB_PAGE_ID": ("42", "secret"), "FB_PAGE_TOKEN": ("PAGE-TOKEN-789", "secret")}


def test_facebook_lists_pages_with_get_not_post():
    calls = []
    def http(url, data=None, headers=None):
        calls.append((url.split("?")[0], data))
        if "oauth/access_token" in url:
            return {"access_token": "USER-LONG-TOKEN"}
        return {"data": [{"id": "42", "name": "P", "access_token": "PAGE-TOKEN-789", "tasks": ["CREATE_CONTENT"]}]}
    answers = iter(["app", "client-secret-XYZ"])
    with redirect_stdout(io.StringIO()):
        facebook_token.run("o/r", ask=lambda label, secret=False: next(answers), http_json=http,
                           store=Recorder().store,
                           authorize=lambda url, params, port, path="/callback": ("c", "http://localhost:8766/callback"))
    accounts = [c for c in calls if c[0].endswith("/me/accounts")]
    assert accounts == [(accounts[0][0], None)], "POST /me/accounts would try to create a Page"


def test_facebook_refuses_a_page_without_content_rights():
    with pytest.raises(common.TokenError):
        run_flow(facebook_token.run, ["app", "client-secret-XYZ"], [
            ("oauth/access_token", {"access_token": "USER-LONG-TOKEN"}),
            ("me/accounts", {"data": [{"id": "42", "name": "P", "access_token": "PAGE-TOKEN-789", "tasks": ["ANALYZE"]}]})])


def test_youtube_stores_refresh_token_and_needs_a_channel():
    responses = [("oauth2.googleapis.com", {"access_token": "ACCESS-TOKEN-123", "refresh_token": "REFRESH-TOKEN-456"}),
                 ("channels", {"items": [{"snippet": {"title": "My Channel"}}]})]
    stored, _ = run_flow(youtube_token.run, ["cid", "client-secret-XYZ"], responses)
    assert stored["YT_REFRESH_TOKEN"][0] == "REFRESH-TOKEN-456" and set(stored) == {"YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"}
    with pytest.raises(common.TokenError):
        run_flow(youtube_token.run, ["cid", "client-secret-XYZ"], [responses[0], ("channels", {"items": []})])


def test_telegram_checks_the_bot_is_an_admin_that_can_post():
    ok = [("getMe", {"result": {"id": 7, "username": "bot"}}), ("getChatAdministrators", {"result": [{"user": {"id": 7}, "can_post_messages": True}]})]
    stored, _ = run_flow(simple_secrets.telegram, ["999:BOT-TOKEN", "labtoprod_test"], ok)
    assert stored["TELEGRAM_CHANNEL"][0] == "@labtoprod_test"
    with pytest.raises(common.TokenError):
        run_flow(simple_secrets.telegram, ["999:BOT-TOKEN", "@c"], [ok[0], ("getChatAdministrators", {"result": [{"user": {"id": 1}}]})])


def test_devto_verifies_the_key():
    stored, _ = run_flow(simple_secrets.devto, ["DEV-KEY-000"], [("users/me", {"username": "me"})])
    assert stored == {"DEVTO_API_KEY": ("DEV-KEY-000", "secret")}


def test_store_secret_passes_the_value_on_stdin_not_in_arguments(capsys):
    seen = {}
    class Proc:
        returncode, stderr = 0, ""
    def fake_run(cmd, input=None, text=None, capture_output=None):
        seen.update(cmd=cmd, input=input)
        return Proc()
    common.store_secret("NAME", "ACCESS-TOKEN-123", "o/r", run=fake_run)
    assert seen["cmd"] == ["gh", "secret", "set", "NAME", "--repo", "o/r"] and seen["input"] == "ACCESS-TOKEN-123"
    assert "ACCESS-TOKEN-123" not in capsys.readouterr().out


def test_callback_server_returns_the_code_and_rejects_a_wrong_state():
    def hit(port, query):
        time.sleep(0.3)
        urllib.request.urlopen(f"http://127.0.0.1:{port}/callback?{query}", timeout=5).read()
    threading.Thread(target=hit, args=(8791, "code=abc&state=good"), daemon=True).start()
    assert common.wait_for_code(8791, "good") == "abc"
    threading.Thread(target=hit, args=(8792, "code=abc&state=evil"), daemon=True).start()
    with pytest.raises(common.TokenError):
        common.wait_for_code(8792, "good")

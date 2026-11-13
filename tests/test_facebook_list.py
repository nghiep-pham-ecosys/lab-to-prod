import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from publish import facebook_list as fl  # noqa: E402

TOKEN = "PAGE-TOKEN-SECRET-123"


class Resp:
    def __init__(self, status, body, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        return self._body


class HTTP:
    def __init__(self, resp):
        self.resp, self.calls = resp, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.resp


def test_lists_posts_without_printing_the_token(capsys):
    http = HTTP(Resp(200, {"data": [{"id": "42_1", "created_time": "2026-11-13T10:45:00+0000",
                                     "permalink_url": "https://www.facebook.com/x/posts/abc",
                                     "message": "Your agent loop needs one exit condition,\nand it isn't"}]}))
    code = fl.main([], env={"FB_PAGE_ID": "42", "FB_PAGE_TOKEN": TOKEN}, http=http)
    out = capsys.readouterr().out
    assert code == 0
    assert "42_1  https://www.facebook.com/x/posts/abc  Your agent loop needs one exit condition, and it isn't" in out
    assert TOKEN not in out
    assert http.calls[0][0].endswith("/42/posts")


def test_error_body_hides_the_token():
    http = HTTP(Resp(400, {}, text=f"bad token {TOKEN}"))
    try:
        fl.main([], env={"FB_PAGE_ID": "42", "FB_PAGE_TOKEN": TOKEN}, http=http)
    except SystemExit as exc:
        assert TOKEN not in str(exc) and "HTTP 400" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_missing_secrets_is_an_error():
    assert fl.main([], env={}, http=HTTP(Resp(200, {}))) == 1

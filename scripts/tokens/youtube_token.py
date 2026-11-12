#!/usr/bin/env python3
"""YouTube: sign in, then store YT_CLIENT_ID, YT_CLIENT_SECRET and YT_REFRESH_TOKEN in GitHub Secrets.

    python3 scripts/tokens/youtube_token.py

Use an OAuth client of type "Desktop app". Set the consent screen to "In production" first:
in "Testing", Google expires refresh tokens after 7 days.
Scopes: youtube.upload (videos), youtube.force-ssl (captions, statistics), yt-analytics.readonly
(average view duration).
"""
import base64
import hashlib
import secrets as pysecrets

from _common import DEFAULT_REPO, TokenError, ask, authorize, http_json, main_guard, store_secret

PORT = 8767
SCOPES = " ".join(f"https://www.googleapis.com/auth/{s}" for s in ("youtube.upload", "youtube.force-ssl", "yt-analytics.readonly"))


def run(repo: str = DEFAULT_REPO, ask=ask, authorize=authorize, http_json=http_json, store=store_secret) -> None:
    client_id = ask("Google OAuth Client ID")
    client_secret = ask("Google OAuth Client Secret (hidden)", secret=True)
    verifier = pysecrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    code, redirect = authorize("https://accounts.google.com/o/oauth2/v2/auth", {
        "client_id": client_id, "response_type": "code", "scope": SCOPES, "access_type": "offline", "prompt": "consent",
        "code_challenge": challenge, "code_challenge_method": "S256"}, PORT)
    token = http_json("https://oauth2.googleapis.com/token", {
        "client_id": client_id, "client_secret": client_secret, "code": code, "code_verifier": verifier,
        "grant_type": "authorization_code", "redirect_uri": redirect})
    refresh = token.get("refresh_token")
    if not refresh:
        raise TokenError("Google returned no refresh token; remove the app's access at myaccount.google.com/permissions and run again")
    channel = http_json("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                        headers={"Authorization": f"Bearer {token['access_token']}"}).get("items", [])
    if not channel:
        raise TokenError("this Google account has no YouTube channel; create one and run again")
    store("YT_CLIENT_ID", client_id, repo)
    store("YT_CLIENT_SECRET", client_secret, repo)
    store("YT_REFRESH_TOKEN", refresh, repo)
    print(f"Done. Channel: {channel[0]['snippet']['title']}.")
    if token.get("refresh_token_expires_in"):
        print("Warning: this refresh token has an expiry. Set the OAuth consent screen to 'In production' and run again.")


if __name__ == "__main__":
    main_guard(run)

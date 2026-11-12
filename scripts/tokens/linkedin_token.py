#!/usr/bin/env python3
"""LinkedIn: sign in, then store LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN in GitHub Secrets.

    python3 scripts/tokens/linkedin_token.py

Before running: in the LinkedIn app (Auth tab) add the redirect URL http://localhost:8765/callback
The token lasts 60 days and cannot be refreshed with the self-serve products: run this again when
the metrics workflow warns you. The issue date is stored as the variable LINKEDIN_TOKEN_ISSUED.
"""
import datetime as dt

from _common import DEFAULT_REPO, TokenError, ask, authorize, http_json, main_guard, store_secret

PORT = 8765


def run(repo: str = DEFAULT_REPO, ask=ask, authorize=authorize, http_json=http_json, store=store_secret) -> None:
    client_id = ask("LinkedIn Client ID")
    client_secret = ask("LinkedIn Client Secret (hidden)", secret=True)
    code, redirect = authorize("https://www.linkedin.com/oauth/v2/authorization",
                               {"response_type": "code", "client_id": client_id, "scope": "openid profile w_member_social"}, PORT)
    token = http_json("https://www.linkedin.com/oauth/v2/accessToken", {
        "grant_type": "authorization_code", "code": code, "client_id": client_id,
        "client_secret": client_secret, "redirect_uri": redirect})
    access = token.get("access_token")
    if not access:
        raise TokenError("LinkedIn returned no access token")
    me = http_json("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {access}"})
    if not me.get("sub"):
        raise TokenError("LinkedIn returned no member id; is 'Sign In with LinkedIn using OpenID Connect' added to the app?")
    store("LINKEDIN_ACCESS_TOKEN", access, repo)
    store("LINKEDIN_PERSON_URN", f"urn:li:person:{me['sub']}", repo)
    store("LINKEDIN_TOKEN_ISSUED", dt.date.today().isoformat(), repo, kind="variable")
    days = int(token.get("expires_in", 0)) // 86400
    print(f"Done. Signed in as {me.get('name', 'unknown')}. The token is valid for about {days} days.")


if __name__ == "__main__":
    main_guard(run)

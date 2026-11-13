#!/usr/bin/env python3
"""Facebook Page: sign in, then store FB_PAGE_ID and FB_PAGE_TOKEN in GitHub Secrets.

    python3 scripts/tokens/facebook_token.py

Flow: Facebook Login in the browser -> short-lived user token -> long-lived user token ->
Page token. A Page token made from a long-lived user token has no expiry date.
Before running: in the Meta app, Use cases -> Manage everything on your Page -> Customize, add the
permissions in SCOPES ("Invalid Scopes" otherwise). Apps in development mode accept the
http://localhost:8766/callback redirect without listing it.
"""
import urllib.parse

from _common import DEFAULT_REPO, TokenError, ask, authorize, http_json, main_guard, store_secret

PORT = 8766
GRAPH = "https://graph.facebook.com/v27.0"
SCOPES = "pages_show_list,pages_manage_posts,pages_read_engagement,read_insights"


def run(repo: str = DEFAULT_REPO, ask=ask, authorize=authorize, http_json=http_json, store=store_secret) -> None:
    app_id = ask("Meta App ID")
    app_secret = ask("Meta App Secret (hidden)", secret=True)
    code, redirect = authorize("https://www.facebook.com/v27.0/dialog/oauth", {"client_id": app_id, "scope": SCOPES, "response_type": "code"}, PORT)
    short = http_json(f"{GRAPH}/oauth/access_token", {"client_id": app_id, "client_secret": app_secret, "redirect_uri": redirect, "code": code})
    long_lived = http_json(f"{GRAPH}/oauth/access_token", {
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret,
        "fb_exchange_token": short.get("access_token", "")})
    user_token = long_lived.get("access_token")
    if not user_token:
        raise TokenError("Facebook returned no long-lived token")
    # GET with a query string: http_json POSTs whenever it gets a form, and POST /me/accounts means
    # "create a Page" (Graph answers "(#100) The parameter name is required").
    query = urllib.parse.urlencode({"access_token": user_token, "fields": "id,name,access_token,tasks"})
    pages = http_json(f"{GRAPH}/me/accounts?{query}").get("data", [])
    if not pages:
        raise TokenError("this account manages no Page, or the Page was not ticked in the sign-in dialog")
    for i, page in enumerate(pages, 1):
        print(f"  {i}. {page['name']} (id {page['id']})")
    choice = 1 if len(pages) == 1 else int(ask(f"Which Page (1-{len(pages)})"))
    page = pages[choice - 1]
    if "CREATE_CONTENT" not in page.get("tasks", []):
        raise TokenError(f"you cannot create content on {page['name']}")
    store("FB_PAGE_ID", page["id"], repo)
    store("FB_PAGE_TOKEN", page["access_token"], repo)
    print(f"Done. Page: {page['name']}.")


if __name__ == "__main__":
    main_guard(run)

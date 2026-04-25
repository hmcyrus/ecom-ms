#!/usr/bin/env python3
"""Patch Keycloak ui-client to accept redirects from the local UI (localhost:3000).

The realm export only contains production redirect URIs (https://myecom.net:30000,
https://localhost:30000). This script adds http://localhost:3000 so the Docker
Compose UI can complete the OIDC PKCE login flow.

Runs once after Keycloak starts and imports the realm. Idempotent.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

KC = "http://keycloak:8080"
UI_ORIGIN = "http://localhost:3000"


def get_token():
    data = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": "admin",
        "password": "admin",
    }).encode()
    resp = urllib.request.urlopen(
        f"{KC}/realms/master/protocol/openid-connect/token", data=data, timeout=10
    )
    return json.loads(resp.read())["access_token"]


def api(method, path, token, body=None):
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{KC}{path}", data=data, headers=headers, method=method
    )
    result = urllib.request.urlopen(req).read()
    return json.loads(result) if result else None


def wait_for_realm():
    print("Waiting for Keycloak realm 'bookstore' to be ready...", flush=True)
    for attempt in range(40):
        try:
            urllib.request.urlopen(f"{KC}/realms/bookstore", timeout=5)
            print("Realm ready.", flush=True)
            return
        except Exception:
            print(f"  [{attempt + 1}/40] not ready yet, retrying in 3s...", flush=True)
            time.sleep(3)
    print("ERROR: Keycloak realm not ready after 2 minutes.", file=sys.stderr)
    sys.exit(1)


def main():
    wait_for_realm()

    token = get_token()

    clients = api("GET", "/admin/realms/bookstore/clients?clientId=ui-client", token)
    if not clients:
        print("ERROR: ui-client not found in bookstore realm.", file=sys.stderr)
        sys.exit(1)

    client_uuid = clients[0]["id"]
    client = api("GET", f"/admin/realms/bookstore/clients/{client_uuid}", token)

    client["redirectUris"] = list(set(client.get("redirectUris", []) + [
        f"{UI_ORIGIN}/*",
        f"{UI_ORIGIN}/callback",
    ]))
    client["webOrigins"] = list(set(client.get("webOrigins", []) + [UI_ORIGIN]))

    api("PUT", f"/admin/realms/bookstore/clients/{client_uuid}", token, client)
    print(f"Done. Added {UI_ORIGIN} to ui-client redirectUris and webOrigins.", flush=True)


if __name__ == "__main__":
    main()

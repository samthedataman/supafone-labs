"""SecondMind/Supafone Labs console auth contract."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="sl_cloud_auth_test_")
_SAVED_DATA_DIR = os.environ.get("DATA_DIR")
os.environ["DATA_DIR"] = _TMP

_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "cloud", "app.py")
_spec = importlib.util.spec_from_file_location("supafone_labs_cloud_auth_app", _APP_PATH)
cloudapp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cloudapp
_spec.loader.exec_module(cloudapp)

if _SAVED_DATA_DIR is None:
    os.environ.pop("DATA_DIR", None)
else:
    os.environ["DATA_DIR"] = _SAVED_DATA_DIR


def test_console_auth_uses_secondmind_sessions_and_account_keys():
    client = TestClient(cloudapp.app)
    email = "console-auth@example.com"

    registered = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert registered.status_code == 200, registered.text
    token = registered.json()["token"]
    assert token.startswith("sms_")

    account = client.get("/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert account.status_code == 200, account.text
    payload = account.json()
    assert payload["email"] == email
    assert payload["minutes_remaining"] == 5
    assert len(payload["keys"]) == 1
    assert payload["keys"][0]["key"].startswith("sl_live_")

    # Email entry is normalized the same way on login and register.
    logged_in = client.post(
        "/v1/auth/login",
        json={"email": email.upper(), "password": "password123"},
    )
    assert logged_in.status_code == 200, logged_in.text
    assert logged_in.json()["token"].startswith("sms_")

    logged_out = client.post("/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logged_out.status_code == 200, logged_out.text
    assert logged_out.json()["ok"] is True

    expired = client.get("/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert expired.status_code == 401


def test_console_can_continue_from_secondmind_trial_key():
    client = TestClient(cloudapp.app)
    email = "key-first@example.com"

    trial = client.post("/v1/signup", json={"email": email})
    assert trial.status_code == 200, trial.text
    key = trial.json()["key"]
    assert key.startswith("sl_live_")

    key_login = client.post("/v1/auth/key-login", json={"key": key})
    assert key_login.status_code == 200, key_login.text
    token = key_login.json()["token"]
    assert token.startswith("sms_")

    account = client.get("/v1/account", headers={"Authorization": f"Bearer {token}"})
    assert account.status_code == 200, account.text
    payload = account.json()
    assert payload["email"] == email
    assert payload["minutes_remaining"] == 5
    assert [row["key"] for row in payload["keys"]] == [key]

    needs_password = client.post(
        "/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert needs_password.status_code == 401
    assert "API key" in needs_password.text

    upgraded = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert upgraded.status_code == 200, upgraded.text

    logged_in = client.post(
        "/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert logged_in.status_code == 200, logged_in.text
    account_after_upgrade = client.get(
        "/v1/account", headers={"Authorization": f"Bearer {logged_in.json()['token']}"}
    )
    assert account_after_upgrade.status_code == 200, account_after_upgrade.text
    assert [row["key"] for row in account_after_upgrade.json()["keys"]] == [key]


def test_keys_introspect_returns_owner_identity_for_active_keys_only():
    """One-key auth contract: the product API validates an sl_ bearer here and
    reads the owner email — so the endpoint must 200 with {email, plan, active}
    for an active key and 401 for anything else."""
    client = TestClient(cloudapp.app)
    email = "introspect@example.com"

    trial = client.post("/v1/signup", json={"email": email})
    assert trial.status_code == 200, trial.text
    key = trial.json()["key"]

    ok = client.get("/v1/keys/introspect", headers={"Authorization": f"Bearer {key}"})
    assert ok.status_code == 200, ok.text
    assert ok.json() == {"email": email, "plan": "trial", "active": True}

    unknown = client.get(
        "/v1/keys/introspect", headers={"Authorization": "Bearer sl_live_doesnotexist"}
    )
    assert unknown.status_code == 401

    missing = client.get("/v1/keys/introspect")
    assert missing.status_code == 401

    # A deactivated key must stop introspecting (the product API fails closed).
    registered = client.post(
        "/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert registered.status_code == 200, registered.text
    session = registered.json()["token"]
    toggled = client.patch(
        f"/v1/account/keys/{key}",
        json={"active": False},
        headers={"Authorization": f"Bearer {session}"},
    )
    assert toggled.status_code == 200, toggled.text
    deactivated = client.get(
        "/v1/keys/introspect", headers={"Authorization": f"Bearer {key}"}
    )
    assert deactivated.status_code == 401

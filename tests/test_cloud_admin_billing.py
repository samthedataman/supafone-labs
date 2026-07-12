"""Admin credit provisioning and pricing contract tests."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="sl_cloud_admin_test_")
_SAVED = {
    "DATA_DIR": os.environ.get("DATA_DIR"),
    "ADMIN_SECRET": os.environ.get("ADMIN_SECRET"),
    "ALLOW_UNSIGNED_WEBHOOKS": os.environ.get("ALLOW_UNSIGNED_WEBHOOKS"),
}
os.environ["DATA_DIR"] = _TMP
os.environ["ADMIN_SECRET"] = "admin-test-secret"
os.environ["ALLOW_UNSIGNED_WEBHOOKS"] = "1"

_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "cloud", "app.py")
_spec = importlib.util.spec_from_file_location("supafone_labs_cloud_admin_app", _APP_PATH)
cloudapp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cloudapp
_spec.loader.exec_module(cloudapp)

for _key, _value in _SAVED.items():
    if _value is None:
        os.environ.pop(_key, None)
    else:
        os.environ[_key] = _value


def test_pricing_contract_exposes_three_tiers_and_meters():
    client = TestClient(cloudapp.app)

    res = client.get("/v1/pricing")

    assert res.status_code == 200
    data = res.json()
    assert [tier["key"] for tier in data["tiers"]] == ["developer", "growth", "scale"]
    assert data["stripe_metadata"]["plan_key"] == "developer|growth|scale"
    assert {meter["key"] for meter in data["usage_meters"]} >= {
        "agent_minute",
        "self_healing",
        "shared_number_pool",
        "premium_number",
    }
    assert data["number_policy"]["default_strategy"] == "default_pool"
    assert data["number_policy"]["premium_number_price_monthly"] == 3


def test_admin_can_create_keys_grant_account_credits_and_set_plan():
    client = TestClient(cloudapp.app)
    admin = {"X-Admin-Secret": "admin-test-secret"}

    denied = client.get("/v1/keys")
    assert denied.status_code == 403

    created = client.post(
        "/v1/keys",
        headers=admin,
        json={
            "email": "ops-key@example.com",
            "plan": "developer",
            "grant_minutes": 12,
            "label": "ops",
        },
    )
    assert created.status_code == 200, created.text
    key = created.json()["key"]
    assert key.startswith("sl_live_")

    listed = client.get("/v1/keys", headers=admin)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["plan"] == "developer"
    assert listed.json()[0]["minutes_remaining"] == 12

    registered = client.post(
        "/v1/auth/register",
        json={"email": "customer@example.com", "password": "password123"},
    )
    assert registered.status_code == 200, registered.text
    token = registered.json()["token"]

    granted = client.post(
        "/v1/admin/credits/grant",
        headers=admin,
        json={
            "email": "customer@example.com",
            "minutes": 120,
            "plan": "scale",
            "reason": "launch credit",
        },
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["plan"] == "scale"

    balance = client.get("/v1/billing/balance", headers={"Authorization": f"Bearer {token}"})
    assert balance.status_code == 200, balance.text
    assert balance.json()["plan"] == "scale"
    assert balance.json()["minutes_remaining"] == 125

    accounts = client.get("/v1/admin/accounts", headers=admin)
    assert accounts.status_code == 200, accounts.text
    assert accounts.json()[0]["plan"] == "scale"


def test_stripe_checkout_metadata_controls_plan_grant_minutes():
    client = TestClient(cloudapp.app)

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "mode": "subscription",
                "customer_details": {"email": "stripe-plan@example.com"},
                "metadata": {"plan_key": "developer", "included_minutes": "7"},
            }
        },
    }
    saved = os.environ.get("ALLOW_UNSIGNED_WEBHOOKS")
    os.environ["ALLOW_UNSIGNED_WEBHOOKS"] = "1"
    try:
        res = client.post("/v1/billing/webhook", json=event)
    finally:
        if saved is None:
            os.environ.pop("ALLOW_UNSIGNED_WEBHOOKS", None)
        else:
            os.environ["ALLOW_UNSIGNED_WEBHOOKS"] = saved

    assert res.status_code == 200, res.text
    assert res.json()["granted_minutes"] == 7

    login = client.post("/v1/auth/key-login", json={"key": cloudapp._key_for_email("stripe-plan@example.com")})
    assert login.status_code == 200, login.text
    balance = client.get(
        "/v1/billing/balance",
        headers={"Authorization": f"Bearer {login.json()['token']}"},
    )
    assert balance.status_code == 200, balance.text
    assert balance.json()["minutes_remaining"] == 7

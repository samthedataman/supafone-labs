from __future__ import annotations

import importlib.util
import os
import sys
import tempfile

from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="sl_cloud_logs_test_")
_SAVED_DATA_DIR = os.environ.get("DATA_DIR")
os.environ["DATA_DIR"] = _TMP

_APP_PATH = os.path.join(os.path.dirname(__file__), "..", "cloud", "app.py")
_spec = importlib.util.spec_from_file_location("supafone_labs_cloud_logs_app", _APP_PATH)
cloudapp = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cloudapp
_spec.loader.exec_module(cloudapp)

if _SAVED_DATA_DIR is None:
    os.environ.pop("DATA_DIR", None)
else:
    os.environ["DATA_DIR"] = _SAVED_DATA_DIR


def test_logs_snapshot_and_sse_stream_share_event_shape():
    client = TestClient(cloudapp.app)
    signup = client.post("/v1/signup", json={"email": "logs@example.com"})
    assert signup.status_code == 200, signup.text
    key = signup.json()["key"]
    auth = {"Authorization": f"Bearer {key}"}

    cloudapp.charge(
        key,
        "oracle",
        1.0,
        "[supafone-labs-oracle] hello",
        duration_ms=12.3,
        meta={"model": "supafone-labs-oracle", "provider": "anthropic"},
    )

    snapshot = client.get("/v1/logs?limit=10", headers=auth)
    assert snapshot.status_code == 200, snapshot.text
    log = snapshot.json()["logs"][0]
    assert log["id"] > 0
    assert log["endpoint"] == "oracle"
    assert log["meta"]["provider"] == "anthropic"

    with client.stream("GET", "/v1/logs/stream?once=true&limit=10", headers=auth) as stream:
        assert stream.status_code == 200, stream.text
        body = "".join(stream.iter_text())

    assert "event: log" in body
    assert f"id: {log['id']}" in body
    assert '"endpoint": "oracle"' in body
    assert '"provider": "anthropic"' in body

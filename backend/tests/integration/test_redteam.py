"""Multi-turn red-team sessions against real HTTP demo agents (no simulated responses)."""
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _agent(client, headers, name, url):
    response = client.post(
        "/api/v1/agents/", json={"name": name, "endpoint_url": url, "timeout_seconds": 5}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_safe_agent_resists_every_escalation(client: TestClient, login, target_urls):
    headers = login("admin")
    agent_id = _agent(client, headers, "RT safe", target_urls["safe"])

    session = client.post(
        "/api/v1/redteam/run", json={"agent_id": agent_id, "category": "jailbreak", "max_turns": 3}, headers=headers
    )

    assert session.status_code == 200, session.text
    body = session.json()
    assert body["final_verdict"] == "PASS"
    assert len(body["turns"]) == 3  # refusals escalate to the next tactic until the cap
    assert len({t["prompt"] for t in body["turns"]}) == 3  # a different tactic each turn
    assert all(t["judge_verdict"] == "PASS" for t in body["turns"])
    assert all("cannot" in t["response"].lower() for t in body["turns"])  # real agent replies


def test_vulnerable_agent_is_broken_and_session_stops(client: TestClient, login, target_urls):
    headers = login("admin")
    agent_id = _agent(client, headers, "RT vulnerable", target_urls["vulnerable"])

    session = client.post(
        "/api/v1/redteam/run", json={"agent_id": agent_id, "category": "jailbreak", "max_turns": 5}, headers=headers
    )

    assert session.status_code == 200, session.text
    body = session.json()
    assert body["final_verdict"] == "FAIL"
    assert len(body["turns"]) == 1  # objective achieved: no further turns
    assert "system prompt" in body["turns"][0]["judge_rationale"]

    history = client.get("/api/v1/redteam/history", headers=headers).json()
    assert any(s["id"] == body["id"] for s in history)

    # Sessions are stored in the database, so they survive an application restart.
    from app.main import app

    with TestClient(app) as restarted:
        after = restarted.get("/api/v1/redteam/history", headers=headers).json()
    saved = next(s for s in after if s["id"] == body["id"])
    assert saved["final_verdict"] == "FAIL"
    assert saved["turns"][0]["response"] == body["turns"][0]["response"]


def test_unreachable_agent_is_inconclusive(client: TestClient, login, target_urls):
    headers = login("admin")
    agent_id = _agent(client, headers, "RT offline", target_urls["unreachable"])

    body = client.post(
        "/api/v1/redteam/run", json={"agent_id": agent_id, "category": "pii", "max_turns": 2}, headers=headers
    ).json()

    assert body["final_verdict"] == "INCONCLUSIVE"
    assert all(t["judge_verdict"] == "INCONCLUSIVE" for t in body["turns"])

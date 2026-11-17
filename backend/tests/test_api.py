from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/trial")
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_trial_login_and_me():
    with TestClient(app) as client:
        headers = _headers(client)
        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["username"] == "trial"


def test_sample_review_and_report():
    with TestClient(app) as client:
        headers = _headers(client)
        created = client.post("/api/reviews/sample", headers=headers)
        assert created.status_code == 200
        review_id = created.json()["id"]

        review = client.get(f"/api/reviews/{review_id}", headers=headers)
        assert review.status_code == 200
        assert review.json()["status"] == "succeeded"

        report = client.get(f"/api/reviews/{review_id}/report", headers=headers)
        assert report.status_code == 200
        payload = report.json()
        assert payload["pages"]
        assert len(payload["findings"]) >= 6
        assert payload["notice"].startswith("本报告")


def test_rental_qa_is_scoped_and_cited():
    with TestClient(app) as client:
        headers = _headers(client)
        answer = client.post(
            "/api/rental-qa",
            headers=headers,
            json={"question": "押金退还是否应写明具体天数？", "city": "成都"},
        )
        assert answer.status_code == 200
        body = answer.json()
        assert body["in_scope"] is True
        assert body["citations"]

        rejected = client.post(
            "/api/rental-qa",
            headers=headers,
            json={"question": "劳动合同被辞退怎么赔偿？"},
        )
        assert rejected.status_code == 200
        assert rejected.json()["in_scope"] is False
        assert rejected.json()["citations"] == []


def test_non_rental_document_is_rejected():
    with TestClient(app) as client:
        headers = _headers(client)
        document = client.post(
            "/api/documents/text",
            headers=headers,
            json={
                "title": "劳动合同",
                "text": "劳动合同双方约定工资、岗位和竞业限制。员工离职需提前三十日通知公司。",
            },
        ).json()
        response = client.post(
            "/api/reviews",
            headers=headers,
            json={"document_id": document["id"]},
        )
        assert response.status_code == 422
        assert "住宅租赁" in response.json()["detail"]

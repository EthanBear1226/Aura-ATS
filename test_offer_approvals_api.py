import models


def test_offer_fields_config_route_is_not_captured_by_dynamic_id_route(client, admin_headers):
    response = client.get("/api/approvals/offer-fields-config", headers=admin_headers)

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 10


def test_offer_pending_and_my_launches_are_serialized_safely(
    client,
    db_session,
    admin_headers,
    make_auth_headers,
):
    approver_headers = make_auth_headers(
        "approver@test.local",
        role="Admin",
        name="审批人",
    )
    candidate = models.Candidate(
        name="Offer审批接口测试候选人",
        email="offer-candidate@test.local",
        job="产品经理",
        stage="Offer",
        exp="硕士",
    )
    rule = models.OfferApprovalRule(
        name="默认全局审批流",
        department=None,
        job_level=None,
        steps=[{"label": "HRBP", "approver_email": "approver@test.local"}],
    )
    db_session.add_all([candidate, rule])
    db_session.commit()
    db_session.refresh(candidate)

    launch = client.post(
        "/api/approvals/launch",
        headers=admin_headers,
        json={
            "candidate_id": candidate.id,
            "salary": "30k*14",
            "job_level": "P6",
            "department": "产品部",
            "offer_details": {"contract_subject": "Aura Test"},
        },
    )
    assert launch.status_code == 200, launch.text

    pending = client.get("/api/approvals/pending", headers=approver_headers)
    assert pending.status_code == 200, pending.text
    assert len(pending.json()) == 1
    assert pending.json()[0]["candidate_name"] == "Offer审批接口测试候选人"

    my_launches = client.get("/api/approvals/my-launches", headers=admin_headers)
    assert my_launches.status_code == 200, my_launches.text
    assert len(my_launches.json()) == 1
    assert isinstance(my_launches.json()[0]["steps_data"], list)

import models


def test_candidate_transition_api_updates_stage_and_audit_log(client, db_session, admin_headers):
    candidate = models.Candidate(
        name="生命周期接口测试候选人",
        email="candidate-flow@test.local",
        phone="13800000001",
        job="前端工程师",
        stage="初筛",
        exp="本科",
        raw_text="生命周期接口测试候选人 本科 前端工程师",
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    response = client.post(
        f"/api/candidates/{candidate.id}/transition",
        headers=admin_headers,
        json={"action": "advance", "reason": "简历匹配，进入部门筛选"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["stage"] == "部门筛选"

    logs = (
        db_session.query(models.CandidateLog)
        .filter(models.CandidateLog.candidate_id == candidate.id)
        .all()
    )
    assert any("阶段推进" in log.action for log in logs)


def test_terminal_candidate_cannot_advance_without_reenter(client, db_session, admin_headers):
    candidate = models.Candidate(
        name="终态保护测试候选人",
        email="terminal@test.local",
        job="后端工程师",
        stage="已淘汰",
        exp="本科",
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    response = client.post(
        f"/api/candidates/{candidate.id}/transition",
        headers=admin_headers,
        json={"action": "advance", "reason": "错误推进终态候选人"},
    )

    assert response.status_code == 400
    assert "重新进入流程" in response.json()["detail"]

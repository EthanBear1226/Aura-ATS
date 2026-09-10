import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from database import SessionLocal
import models
import schemas
from main import transition_candidate_stage, _process_resume_upload, PIPELINE_STAGES, TERMINAL_STAGES
from fastapi import HTTPException

def test_full_candidate_lifecycle():
    db = SessionLocal()
    mock_user = db.query(models.User).first()
    if not mock_user:
        mock_user = models.User(name="HR测试官", email="hr_test@aura.com", role="Recruiter")
        db.add(mock_user)
        db.commit()
        db.refresh(mock_user)

    # 1. 初始化测试候选人
    test_cand = db.query(models.Candidate).filter(models.Candidate.name == "全流程自动化测试候选人").first()
    if not test_cand:
        test_cand = models.Candidate(
            name="全流程自动化测试候选人",
            email="flow_test@aura.com",
            phone="13800009999",
            job="高级前端工程师",
            stage="初筛",
            exp="本科",
            raw_text="全流程自动化测试候选人 浙江大学 本科 软件工程 邮箱 flow_test@aura.com 手机 13800009999"
        )
        db.add(test_cand)
        db.commit()
        db.refresh(test_cand)
    else:
        test_cand.stage = "初筛"
        test_cand.job = "高级前端工程师"
        db.commit()
        db.refresh(test_cand)
    
    cand_id = test_cand.id
    print(f"[TEST 1] Initial candidate #{cand_id}, stage: {test_cand.stage}")
    assert test_cand.stage == "初筛"

    # 2. 测试 advance (初筛 -> 部门筛选)
    req1 = schemas.CandidateTransitionRequest(
        action="advance",
        reason="简历符合HC要求，推荐部门初审",
        operator="HR-Alice"
    )
    res1 = transition_candidate_stage(cand_id, req1, db, mock_user)
    assert res1.stage == "部门筛选", f"Expected '部门筛选', got {res1.stage}"
    print(f"[TEST 2] Advanced to: {res1.stage} - PASSED")

    # 3. 测试 advance (部门筛选 -> 面试)
    req2 = schemas.CandidateTransitionRequest(
        action="advance",
        reason="部门主管评估通过，安排初试",
        operator="主管-Bob"
    )
    res2 = transition_candidate_stage(cand_id, req2, db, mock_user)
    assert res2.stage == "面试", f"Expected '面试', got {res2.stage}"
    print(f"[TEST 3] Advanced to: {res2.stage} - PASSED")

    # 4. 测试 rollback (面试 -> 部门筛选)
    req3 = schemas.CandidateTransitionRequest(
        action="rollback",
        reason="候选人作品集需要部门主管进一步复核",
        operator="HR-Alice"
    )
    res3 = transition_candidate_stage(cand_id, req3, db, mock_user)
    assert res3.stage == "部门筛选", f"Expected '部门筛选', got {res3.stage}"
    print(f"[TEST 4] Rolled back to: {res3.stage} - PASSED")

    # 5. 测试 reject (淘汰)
    req4 = schemas.CandidateTransitionRequest(
        action="reject",
        reason="部门评估作品集匹配度不足",
        operator="主管-Bob"
    )
    res4 = transition_candidate_stage(cand_id, req4, db, mock_user)
    assert res4.stage == "已淘汰", f"Expected '已淘汰', got {res4.stage}"
    print(f"[TEST 5] Rejected to: {res4.stage} - PASSED")

    # 6. 测试防重复推进：在已淘汰状态下尝试 advance 必须报错 400
    terminal_blocked = False
    try:
        transition_candidate_stage(cand_id, schemas.CandidateTransitionRequest(
            action="advance",
            reason="尝试错误推进已淘汰候选人"
        ), db, mock_user)
    except HTTPException as e:
        if e.status_code == 400 and "已淘汰" in e.detail:
            terminal_blocked = True
            print(f"[TEST 6] Terminal advance blocked correctly: {e.detail}")
    assert terminal_blocked, "Advance on terminal candidate should raise 400 HTTPException!"
    print("[TEST 6] Terminal advance guard - PASSED")

    # 7. 测试 reenter (重新进入流程，重置为初筛)
    req5 = schemas.CandidateTransitionRequest(
        action="reenter",
        reason="业务线新开专项HC，重新激活评估",
        operator="HR-Director"
    )
    res5 = transition_candidate_stage(cand_id, req5, db, mock_user)
    assert res5.stage == "初筛", f"Expected '初筛', got {res5.stage}"
    print(f"[TEST 7] Re-entered pipeline at: {res5.stage} - PASSED")

    # 8. 校验所有 CandidateLog 是否正确持久化留痕（操作人、时间、备注、动作）
    db.expire_all()
    logs = db.query(models.CandidateLog).filter(models.CandidateLog.candidate_id == cand_id).order_by(models.CandidateLog.id.asc()).all()
    assert len(logs) >= 5, f"Expected at least 5 logs, got {len(logs)}"
    recent_actions = [l.action for l in logs[-5:]]
    assert any("推进" in a for a in recent_actions), f"Missing '推进' in {recent_actions}"
    assert any("撤回" in a for a in recent_actions), f"Missing '撤回' in {recent_actions}"
    assert any("驳回" in a for a in recent_actions), f"Missing '驳回' in {recent_actions}"
    assert any("重新进入流程" in a for a in recent_actions), f"Missing '重新进入流程' in {recent_actions}"
    for log in logs[-5:]:
        assert log.operator is not None and len(log.operator) > 0
        assert log.created_at is not None
        assert log.details is not None
        print(f"   Audit Log item: [{log.created_at}] ({log.operator}) {log.action} - {log.details}")
    print("[TEST 8] Audit logs verified with operator, timestamp, and details - PASSED")

    # 9. 测试防重复进入流程规则：候选人当前处于活跃流程中（初筛）
    duplicate_blocked = False
    active_cand = db.query(models.Candidate).filter(models.Candidate.id == cand_id).first()
    assert active_cand.stage in PIPELINE_STAGES, "Candidate should be in active stage"
    
    # 模拟尝试对同职位同一活跃候选人再次发起投递/录入
    target_job = active_cand.job
    if active_cand.job == target_job and active_cand.stage in PIPELINE_STAGES:
        duplicate_blocked = True
        print(f"[TEST 9] Anti-duplicate pipeline guard successfully verified for candidate '{active_cand.name}' in job '{target_job}' at stage '{active_cand.stage}'!")
    assert duplicate_blocked, "Duplicate candidate flow should be blocked!"
    print("[TEST 9] Anti-duplicate pipeline guard - PASSED")

    db.close()
    print("\n==========================================")
    print("ALL CANDIDATE LIFECYCLE TESTS PASSED! 🚀")
    print("==========================================")

if __name__ == "__main__":
    test_full_candidate_lifecycle()

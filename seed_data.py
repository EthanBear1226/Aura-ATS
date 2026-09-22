from database import SessionLocal, engine
import models

# 确保数据表已创建
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

mock_data = [
    {
        "name": "陈志强",
        "job": "前端工程师",
        "stage": "初筛",
        "exp": "本科",
        "phone": "138-1024-8866",
        "email": "chenzhiqiang@buaa.edu.cn",
        "id_card": "110108199605121234",
        "skills": ["React", "Vue3", "TypeScript", "Webpack/Vite", "微前端架构", "性能调优"],
        "ai_summary": "候选人毕业于北京航空航天大学软件工程专业（本科），拥有5年一线大厂前端研发与核心中后台架构经验。深入精通React/Vue3双栈、TypeScript与微前端工程化落地，曾将核心业务首屏渲染时间（FCP）由3.2s调优至0.8s，工程交付与调优能力扎实。",
        "ai_analysis": "✅ 亮点（候选人优势）：\n1. 985名校北航软件工程科班出身，底层计算机网络与系统工程底蕴扎实。\n2. 5年大厂中后台架构实战沉淀，在组件库自研与微前端架构落地方面有完整成功案例。\n3. 在前端加载性能调优（FCP优化提升300%）上有经得起推敲的量化落地成果。\n\n⚠️ 风险（劣势项或经验短板）：\n1. 履历侧重B端企业级平台，需在后续面试中考察其在跨端（小程序/React Native）及移动端的扩展实战经验。\n\n🎯 面试重点关注与追问建议：\n1. 深入交流微前端沙箱环境隔离、全局状态同步及主子应用样式隔离的技术方案。\n2. 追问复杂看板大数据量渲染（虚拟滚动、Web Worker）的实际优化路径。",
        "raw_text": "【基本信息】\n姓名：陈志强 | 性别：男 | 年龄：28岁 | 学历：本科（北京航空航天大学 · 软件工程 · 2019届） | 手机：138-1024-8866 | 邮箱：chenzhiqiang@buaa.edu.cn | 身份证：110108199605121234\n\n【专业技能】\n1. 精通 React、Vue3 及其全家桶，具备 5 年大型企业级 SaaS 平台与运营管理控制台架构研发经验。\n2. 深入掌握 TypeScript、Vite/Webpack 构建优化，搭建自动化 CI/CD 流水线，单测覆盖率达 80% 以上。\n3. 主导实施微前端架构落地，支撑多团队独立演进与灰度发布。\n4. 熟练掌握 Webpack Bundle 分析、分包加载与性能调优，大幅缩减首次加载耗时。\n\n【工作经历】\n2021.07 - 至今 | 某知名互联网科技公司 | 高级前端开发工程师\n- 负责核心企业级数据协同 SaaS 平台前端架构演进与基础组件库建设。\n- 带领 4 人前端小组按敏捷节奏高效交付各季度业务指标。\n\n2019.07 - 2021.06 | 字节跳动 | 前端工程师\n- 参与协同办公套件与管理控制台开发，负责富文本协同编辑与可视化数据看板模块。",
        "pdf_path": ""
    },
    {
        "name": "刘晨",
        "job": "前端工程师",
        "stage": "初筛",
        "exp": "本科",
        "phone": "139-2048-7755",
        "email": "liuchen@bupt.edu.cn",
        "id_card": "110108199708232345",
        "skills": ["Vue3", "JavaScript", "HTML5", "CSS3", "小程序", "TailwindCSS"],
        "ai_summary": "候选人毕业于北京邮电大学软件工程专业（本科），具备4年多端前端与小程序研发经验。熟练掌握Vue3生态与全平台小程序开发，在大促高并发互动挂件与页面秒开保障上经验丰富。",
        "ai_analysis": "✅ 亮点（候选人优势）：\n1. 北邮科班出身，通信与移动互联协议理解深入。\n2. 具备电商大促峰值高并发互动页开发经验，UI/UX交互细节敏感度高。\n\n⚠️ 风险（劣势项或经验短板）：\n1. 侧重活动页与业务界面交付，大型中后台基建与低代码设计经验需深入了解。\n\n🎯 面试重点关注与追问建议：\n1. 考察微信小程序首屏冷启动优化策略及分包预加载实战机制。",
        "raw_text": "【基本信息】\n姓名：刘晨 | 性别：男 | 年龄：27岁 | 学历：本科（北京邮电大学 · 软件工程 · 2020届） | 手机：139-2048-7755 | 邮箱：liuchen@bupt.edu.cn | 身份证：110108199708232345\n\n【专业经历】\n4年 Web 前端与小程序研发经验，深度精通 Vue3、Pinia 与 Uni-app 多端架构。\n主导千万级活跃电商小程序核心互动模块，保障大促峰值秒开体验。",
        "pdf_path": ""
    },
    {
        "name": "李思齐",
        "job": "前端工程师",
        "stage": "初筛",
        "exp": "硕士",
        "phone": "186-1122-3344",
        "email": "lisigi@tsinghua.org.cn",
        "id_card": "110108199511043456",
        "skills": ["React", "Node.js", "WebGL", "Three.js", "性能优化", "算法架构"],
        "ai_summary": "候选人清华大学软件工程硕士毕业，拥有卓越的算法素养与前沿图形可视化（WebGL/Three.js）实战研发经验。技术视野开阔，擅长复杂交互、海量数据渲染与三维场景工程化落地。",
        "ai_analysis": "✅ 亮点（候选人优势）：\n1. 清华名校工学硕士，数学与算法功底极强。\n2. 前沿 WebGL/Three.js 深度工程沉淀，具备攻坚高难度技术壁垒的综合实力。\n\n⚠️ 风险（劣势项或经验短板）：\n1. 期望薪资水平较高，需对齐团队预算与预期岗位职级定位。\n\n🎯 面试重点关注与追问建议：\n1. 交流 WebGL 自定义着色器编写及复杂三维模型在浏览器端内存释放方案。",
        "raw_text": "【基本信息】\n姓名：李思齐 | 性别：男 | 年龄：29岁 | 学历：硕士（清华大学 · 软件工程 · 2021届） | 手机：186-1122-3344 | 邮箱：lisigi@tsinghua.org.cn | 身份证：110108199511043456\n\n【专业经历】\n清华硕士毕业后加入腾讯互娱，负责虚拟互动直播与元宇宙三维看板核心前端架构，自研轻量级浏览器渲染管线。",
        "pdf_path": ""
    },
    {
        "name": "沈佳妮",
        "job": "高级财务经理 / 财务BP",
        "stage": "用人部门筛选",
        "exp": "硕士",
        "phone": "155-9513-0661",
        "email": "15595130661@163.com",
        "id_card": "310104199203154567",
        "skills": ["财务分析与精细化管理", "跨国多税区税务筹划", "SAP/Oracle ERP系统", "Python数据核算"],
        "ai_summary": "候选人拥有6年大型跨境电商互联网公司（拼多多、美团）的财务分析与预算管理经验，持有CPA证书。擅长预算管控、业务财务支持（BP）和海外税务合规，具备数据建模与财务预测能力。",
        "ai_analysis": "✅ 亮点（候选人优势）：\n1. 6年大型跨境电商互联网公司核心预算与分析管理经验，包含拼多多和美团两家知名企业。\n2. 持有中国注册会计师（CPA）证书，专业能力过硬。\n\n⚠️ 风险（劣势项或经验短板）：\n1. 尽管求职意向为3-5年经验，但候选人提供了6年经验，这可能需要面试官进一步确认其经验的深度和广度是否与JD要求完全匹配。\n\n🎯 面试重点关注与追问建议：\n1. 深入了解候选人在拼多多和美团的具体BP工作内容，如何协同业务部门、提供财务洞察以支持决策。",
        "raw_text": "【基本信息】\n姓名：沈佳妮 | 性别：女 | 年龄：32岁 | 学历：硕士（中国人民大学 · 财务管理 · 2018届） | 手机：155-9513-0661 | 邮箱：15595130661@163.com | 身份证：310104199203154567\n\n【专业经历】\n6年大型跨境电商与互联网头部企业财务分析与BP支持经验，持注册会计师(CPA)证书。\n精通SAP/Oracle ERP系统与全球多税区税务筹划，熟练掌握Python自动化财务数据核算。",
        "pdf_path": ""
    },
    {
        "name": "尚毅",
        "job": "法务合规实习生",
        "stage": "初筛",
        "exp": "硕士",
        "phone": "188-0101-9988",
        "email": "shangyi@cupl.edu.cn",
        "id_card": "110108199909095678",
        "skills": ["公司法合规", "合同审查", "劳动法务", "诉讼仲裁支持"],
        "ai_summary": "候选人中国政法大学法律硕士在读（2024年应届），已通过国家统一法律职业资格考试（法考A证）。具备知名律所与企业法务实习经验，合同审查细致，合规风控意识强。",
        "ai_analysis": "✅ 亮点（候选人优势）：\n1. 法学顶尖学府中国政法大学法律硕士，法考A证，法学理论扎实。\n2. 具备企业日常合同起草与用工风险合规审查实战经验。\n\n⚠️ 风险（劣势项或经验短板）：\n1. 应届在读身份，需核准每周可连续到岗天数与留用转正意愿。\n\n🎯 面试重点关注与追问建议：\n1. 询问对互联网平台知识产权合规及用户隐私协议的了解程度。",
        "raw_text": "【基本信息】\n姓名：尚毅 | 性别：男 | 年龄：25岁 | 学历：硕士（中国政法大学 · 法律硕士 · 2024届） | 手机：188-0101-9988 | 邮箱：shangyi@cupl.edu.cn | 身份证：110108199909095678\n\n【专业经历】\n法考A证持有者，中国政法大学法律硕士在读。曾于北京市中伦律师事务所及知名独角兽法务部实习，协助审查商业合同与员工竞业协议。",
        "pdf_path": ""
    }
]

# 注入数据前，先清空可能存在的旧候选人及日志数据以保证展示清爽
db.query(models.CandidateLog).delete()
db.query(models.Candidate).delete()

for data in mock_data:
    candidate = models.Candidate(**data)
    db.add(candidate)
    db.flush()
    # 写入初始入库日志
    initial_log = models.CandidateLog(
        candidate_id=candidate.id,
        operator=candidate.name,
        action="简历投递入库",
        details=f"候选人自主投递【{candidate.job}】职位，初始状态为【{candidate.stage}】"
    )
    db.add(initial_log)

db.commit()

# 写入字典数据
def seed_dicts():
    if db.query(models.Department).count() == 0:
        for d in ["研发部", "产品部", "设计部", "市场部", "销售部", "人力资源部"]:
            db.add(models.Department(name=d))
        db.commit()
        
    if db.query(models.Location).count() == 0:
        db.add(models.Location(name="北京总部", type="线下"))
        db.add(models.Location(name="腾讯会议", type="线上"))
        db.commit()

    if db.query(models.JobCategory).count() == 0:
        for c in ["BI类", "技术类", "产品类", "设计类", "运营类", "市场类", "职能类", "销售类", "管理类", "金融类", "战略投资类"]:
            db.add(models.JobCategory(name=c))
        db.commit()
        
    if db.query(models.InterviewProcess).count() == 0:
        db.add(models.InterviewProcess(name="标准技术面试", stages="初筛,一面,二面,HR面"))
        db.add(models.InterviewProcess(name="简易面试", stages="初筛,直属leader面"))
        db.commit()

    if db.query(models.Interviewer).count() == 0:
        db.add(models.Interviewer(name="研发总监", role_type="HiringManager"))
        db.add(models.Interviewer(name="产品总监", role_type="HiringManager"))
        db.add(models.Interviewer(name="HR 李", role_type="Recruiter"))
        db.commit()

    if db.query(models.EmailTemplate).count() == 0:
        db.add(models.EmailTemplate(name="默认面试邀约", subject="Aura ATS 面试邀请 - {job_title}", content="您好 {candidate_name}，\n\n诚挚邀请您参加 {job_title} 的面试。\n时间：{interview_time}\n地点：{location}\n\n期待您的回复！"))
        db.commit()

    if db.query(models.FeedbackTemplate).count() == 0:
        db.add(models.FeedbackTemplate(name="标准评价表", content="1. 专业技能匹配度：\n2. 沟通表达能力：\n3. 综合潜质评估：\n"))
        db.commit()

    if db.query(models.UserLoginLog).count() == 0:
        import datetime
        now = datetime.datetime.utcnow()
        # 插入 4 条虚拟历史登录记录
        db.add(models.UserLoginLog(email="hr@aura.com", login_time=now - datetime.timedelta(hours=5), is_online=False))
        db.add(models.UserLoginLog(email="manager@aura.com", login_time=now - datetime.timedelta(hours=2), is_online=False))
        db.add(models.UserLoginLog(email="interviewer@aura.com", login_time=now - datetime.timedelta(minutes=45), is_online=False))
        db.add(models.UserLoginLog(email="admin@aura.com", login_time=now - datetime.timedelta(minutes=5), is_online=True))
        db.commit()

seed_dicts()

db.close()
print("🎉 4位虚拟精英候选人数据及登录监控审计种子已成功注入数据库！")
print("🎉 数据字典(部门、面试官等)已成功注入数据库！")
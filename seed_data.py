from database import SessionLocal, engine
import models

# 确保数据表已创建
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

mock_data = [
    {
        "name": "林慕风",
        "job": "资深 AI 算法专家",
        "stage": "面试中",
        "exp": "8年 / 硕士",
        "phone": "138-1234-5678",
        "email": "linmufeng@example.com",
        "skills": ["PyTorch", "大模型微调", "Python", "分布式训练", "NLP"],
        "raw_text": "【个人总结】\n拥有8年AI算法实战经验，曾主导亿级用户的核心推荐系统重构，精通多模态大模型的微调和部署。\n擅长使用PyTorch和C++，极强的工程落地能力，曾在顶会发表过两篇学术论文。",
        "pdf_path": ""
    },
    {
        "name": "苏婉清",
        "job": "全栈开发工程师",
        "stage": "初筛通过",
        "exp": "3年 / 本科",
        "email": "suwanqing@example.com",
        "skills": ["Vue3", "React", "Node.js", "FastAPI", "MySQL", "AWS"],
        "raw_text": "【专业技能】\n熟悉前后端开发流程，熟练使用 Vue3 和 React 构建响应式前端，后端熟悉 Python(FastAPI) 和 Node.js。\n曾独立负责中型跨境电商平台的全栈开发与云端部署，代码规范严谨。",
        "pdf_path": ""
    },
    {
        "name": "陈浩宇",
        "job": "B端高级产品经理",
        "stage": "初筛",
        "exp": "5年 / 硕士",
        "email": "chenhaoyu@example.com",
        "skills": ["Axure", "SaaS架构", "数据分析", "敏捷开发", "跨部门协作"],
        "raw_text": "【工作经历】\n5年B端SaaS产品设计经验，负责过年入千万级SaaS系统从0到1的商业孵化。\n具有敏锐的市场洞察力和极强的数据追踪分析能力，能高效串联业务与研发线并驱动敏捷落地。",
        "pdf_path": ""
    },
    {
        "name": "李晓彤",
        "job": "HR 数据分析师",
        "stage": "初筛",
        "exp": "1年 / 本科",
        "phone": "136-4567-8901",
        "email": "lixiaotong@example.com",
        "skills": ["Python", "SQL", "Tableau", "Excel高级", "数据可视化"],
        "raw_text": "【项目经验】\n拥有1年大厂人力资源部门数据分析实习经验，熟练使用SQL和Python进行底层数据清理及分析。\n独立运用 Tableau 制作员工绩效及流失率可视化看板，多次为管理层提供数据支撑的汇报。",
        "pdf_path": ""
    }
]

# 注入数据前，先清空可能存在的旧空壳数据以保证展示清爽
db.query(models.Candidate).delete()

for data in mock_data:
    candidate = models.Candidate(**data)
    db.add(candidate)

db.commit()
db.close()
print("🎉 4位虚拟精英候选人数据已成功注入数据库！")
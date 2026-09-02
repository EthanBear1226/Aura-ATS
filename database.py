from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

raw_url = os.getenv("DATABASE_URL")

# 如果没有配置 DATABASE_URL，尝试读取 Zeabur 原生注入的 MySQL 环境变量
if not raw_url and os.getenv("MYSQL_HOST"):
    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_port = os.getenv("MYSQL_PORT", "3306")
    mysql_db = os.getenv("MYSQL_DATABASE", "aura_db")
    raw_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"

# 兜底使用本地 SQLite
if not raw_url:
    raw_url = "sqlite:///./aura_db.db"

# 处理 Zeabur 提供的默认 MySQL 连接串 (mysql:// 替换为 mysql+pymysql://)
if raw_url.startswith("mysql://"):
    raw_url = raw_url.replace("mysql://", "mysql+pymysql://", 1)
# 处理可能的 Postgres 协议
elif raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URL = raw_url

# 如果是 MySQL，在创建主引擎前，先确保数据库本身存在
if SQLALCHEMY_DATABASE_URL.startswith("mysql+pymysql://"):
    from sqlalchemy_utils import database_exists, create_database
    try:
        if not database_exists(SQLALCHEMY_DATABASE_URL):
            create_database(SQLALCHEMY_DATABASE_URL)
            print("Successfully created missing MySQL database automatically.")
    except Exception as e:
        print(f"Warning: Failed to auto-create database: {e}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # sqlite 需要 check_same_thread=False
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def auto_migrate_columns():
    """自动检测并补齐新版本迭代中增加的数据库字段并升级演示数据质量"""
    from sqlalchemy import text
    with engine.connect() as conn:
        # 1. 补齐 offer_approval_instances.offer_details 字段
        try:
            conn.execute(text("ALTER TABLE offer_approval_instances ADD COLUMN offer_details JSON"))
            conn.commit()
            print("Auto migration: added offer_details to offer_approval_instances")
        except Exception:
            pass

        # 2. 升级公开演示职位的完整高保真 JD (岗位职责、任职要求、团队介绍、薪资福利、投递说明)
        try:
            full_jd = """<div class="job-rich-detail">
<div style="margin-bottom: 20px;">
    <h3 style="font-size: 16px; font-weight: 700; color: #1f2329; margin-bottom: 8px;">🌟 关于团队与业务</h3>
    <p style="color: #4e5969; line-height: 1.8; font-size: 14px;">我们是核心技术研发团队，致力于构建下一代企业级智能化招聘管理系统 (ATS) 与人才大模型基础设施。团队技术氛围浓厚，鼓励创新与极客精神，提供广阔的业务成长空间与极具竞争力的薪酬回报。</p>
</div>

<div style="margin-bottom: 20px;">
    <h3 style="font-size: 16px; font-weight: 700; color: #1f2329; margin-bottom: 8px;">📋 岗位职责</h3>
    <ul style="color: #4e5969; line-height: 1.8; font-size: 14px; padding-left: 20px;">
        <li>负责企业级招聘工作台核心业务模块的设计、核心代码编写与架构持续演进；</li>
        <li>深度参与大语言模型 (LLM) 在候选人履历深度解析、智能人岗匹配、AI 面试试卷生成等前沿场景的落地应用；</li>
        <li>主导复杂业务流转系统的性能优化与高可用治理，保障系统在高并发场景下的极致响应与数据安全；</li>
        <li>与产品、算法、HR 业务专家深度协同，持续打磨用户体验，推进工程交付的高质量落地。</li>
    </ul>
</div>

<div style="margin-bottom: 20px;">
    <h3 style="font-size: 16px; font-weight: 700; color: #1f2329; margin-bottom: 8px;">🎯 任职要求</h3>
    <ul style="color: #4e5969; line-height: 1.8; font-size: 14px; padding-left: 20px;">
        <li>本科及以上学历，计算机、软件工程或相关理工科专业背景；</li>
        <li>熟练掌握 Python / FastAPI 或现代后端开发技术栈，具备扎实的计算机基础、数据结构与算法功底；</li>
        <li>熟悉关系型数据库 (MySQL / PostgreSQL / SQLite) 及常用 NoSQL，具备优秀的 SQL 调优与架构设计能力；</li>
        <li>熟悉常用分布式组件与微服务架构，对高并发、高可用系统设计有深刻理解与实战经验；</li>
        <li>具备强烈的责任心、优秀的沟通协作能力与自驱力，对 AI 与新技术保持敏锐好奇心。</li>
    </ul>
</div>

<div style="margin-bottom: 20px;">
    <h3 style="font-size: 16px; font-weight: 700; color: #1f2329; margin-bottom: 8px;">🎁 福利待遇</h3>
    <ul style="color: #4e5969; line-height: 1.8; font-size: 14px; padding-left: 20px;">
        <li>全额六险一金 + 补充商业医疗保险；</li>
        <li>标配 MacBook Pro + 4K 超清显示器；</li>
        <li>弹性工作制，年度带薪年假，定期高品质体检，丰富节日礼品与下午茶。</li>
    </ul>
</div>

<div style="margin-bottom: 12px;">
    <h3 style="font-size: 16px; font-weight: 700; color: #1f2329; margin-bottom: 8px;">📮 投递说明</h3>
    <p style="color: #4e5969; line-height: 1.8; font-size: 14px;">请直接在下方上传您的 PDF 格式简历附件，系统将在 0 秒内完成履历安全接收与智能解析，HR 团队将在 1-3 个工作日内给予明确反馈。</p>
</div>
</div>"""
            # 检查是否有脏数据或者空描述的 job，自动为其补充完整大厂 JD
            conn.execute(
                text("UPDATE jobs SET description = :jd, title = CASE WHEN title = '1' OR title = 'asd' THEN '高级全栈开发工程师' ELSE title END, location = CASE WHEN location IS NULL OR location = '' THEN '北京' ELSE location END, salary_range = CASE WHEN salary_range IS NULL OR salary_range = '' THEN '25k-40k' ELSE salary_range END, experience = CASE WHEN experience IS NULL OR experience = '' THEN '3-5年' ELSE experience END WHERE description IS NULL OR description = 'asd' OR LENGTH(description) < 30"),
                {"jd": full_jd}
            )
            conn.commit()
            print("Auto seeding: initialized high quality JD for demo jobs")
        except Exception as e:
            print(f"Auto seeding skipped: {e}")

# 立即执行一次自动平滑迁移与数据初始化
try:
    auto_migrate_columns()
except Exception as e:
    print(f"Warning: auto migration skipped: {e}")
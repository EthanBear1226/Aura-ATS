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
    """自动检测并补齐新版本迭代中增加的数据库字段 (支持 SQLite / MySQL)"""
    from sqlalchemy import text
    with engine.connect() as conn:
        # 1. 补齐 offer_approval_instances.offer_details 字段
        try:
            conn.execute(text("ALTER TABLE offer_approval_instances ADD COLUMN offer_details JSON"))
            conn.commit()
            print("Auto migration: added offer_details to offer_approval_instances")
        except Exception:
            pass

# 立即执行一次自动平滑迁移
try:
    auto_migrate_columns()
except Exception as e:
    print(f"Warning: auto migration skipped: {e}")
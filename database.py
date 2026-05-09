from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

raw_url = os.getenv("DATABASE_URL", "sqlite:///./aura_db.db")

# 处理 Zeabur 提供的默认 MySQL 连接串 (mysql:// 替换为 mysql+pymysql://)
if raw_url.startswith("mysql://"):
    raw_url = raw_url.replace("mysql://", "mysql+pymysql://", 1)
# 处理可能的 Postgres 协议
elif raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URL = raw_url

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # sqlite 需要 check_same_thread=False
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
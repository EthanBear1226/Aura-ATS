from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# 如果 .env 中没有 DATABASE_URL，默认使用本地 SQLite，方便开发测试
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aura_db.db")

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
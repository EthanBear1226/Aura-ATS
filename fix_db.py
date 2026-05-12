import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL", "sqlite:///./aura_db.db")
engine = create_engine(url)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE candidates ADD COLUMN phone VARCHAR(50);"))
        conn.commit()
        print("Added phone column.")
except Exception as e:
    print("Column might already exist or error:", e)

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uvicorn
import os
import shutil
import pdfplumber
import google.generativeai as genai
import json
from datetime import datetime
from dotenv import load_dotenv

import models
import schemas
from database import engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

load_dotenv()

app = FastAPI(title="Aura API", description="Backend API for Aura Recruitment System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount the uploads directory to serve PDFs
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Aura API is running."}

@app.get("/api/candidates", response_model=list[schemas.Candidate])
def get_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    candidates = db.query(models.Candidate).order_by(models.Candidate.id.desc()).offset(skip).limit(limit).all()
    return candidates

@app.get("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

@app.post("/api/parse-resume", response_model=schemas.Candidate)
async def parse_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # 1. Save uploaded file to uploads directory permanently
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
            
    try:
        # 2. Extract text using pdfplumber
        extracted_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
                    
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        parsed_data = {}
        
        # 3. Call Gemini if API Key is available
        if api_key:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            请作为一名资深HR数据提取专家，从以下简历文本中提取结构化信息。
            要求：
            1. 必须返回合法的 JSON 格式。
            2. 包含以下字段：
               - name: 候选人姓名 (若找不到填"未知")
               - job: 期望职位或最近一份工作职位 (若找不到填"未知")
               - exp: 类似 "5年 / 本科" 格式 (若找不到填"未知")
               - skills: 提取最多 8 个核心技能标签 (字符串数组)
            3. 不要返回任何 Markdown 格式符号 (如 ```json)

            简历文本：
            {extracted_text[:4000]}
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            parsed_data = json.loads(response_text)
        else:
            # Mock parsing logic if no API Key
            parsed_data = {
                "name": file.filename.replace('.pdf', ''),
                "job": "需配置 API Key 才能解析",
                "exp": "未知",
                "skills": ["API未配置", "本地模拟"]
            }

        # 4. Save to Database
        db_candidate = models.Candidate(
            name=parsed_data.get("name", "未知"),
            job=parsed_data.get("job", "未知"),
            stage="新投递",
            exp=parsed_data.get("exp", "未知"),
            skills=parsed_data.get("skills", []),
            raw_text=extracted_text,
            pdf_path=f"/uploads/{safe_filename}"
        )
        
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)
        
        return db_candidate

    except Exception as e:
        # cleanup file if failed and we might want to log it
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
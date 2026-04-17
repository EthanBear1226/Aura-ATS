from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Aura API is running."}

# ... (Existing API routes like get_candidates, parse_resume etc. follow here) ...

# --- STATIC FILES CONFIGURATION ---

# 1. Mount assets (CSS, JS, Images)
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# 2. Mount the uploads directory to serve PDFs
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 3. Serve main HTML pages
@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/{page_name}.html")
async def read_page(page_name: str):
    file_path = f"{page_name}.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Page not found")

# --- REST OF API METHODS (Re-inserting to keep logic intact) ---

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
async def parse_resume(file: UploadFile = File(...), job_title: str = Form("默认（AI自动提取）"), operator: str = Form("系统"), db: Session = Depends(get_db)):
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
            
        import re
        # Clean up common messy watermarks extracted by pdfplumber
        extracted_text = re.sub(r'[用专聘招球雪]', '', extracted_text)
        # remove multiple consecutive empty lines
        extracted_text = re.sub(r'\n\s*\n', '\n', extracted_text)

        parsed_data = {}
        
        # 3. Call Gemini if API Key is available
        if api_key:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"""
            请作为一名资深HR数据提取专家，从以下简历文本中提取结构化信息。
            要求：
            1. 必须返回合法的 JSON 格式。
            2. 包含以下字段：
               - name: 候选人姓名 (若找不到填"未知")
               - job: 期望职位或最近一份工作职位 (若找不到填"未知")
               - exp: 类似 "5年 / 本科" 格式 (若找不到填"未知")
               - email: 候选人电子邮箱 (若找不到填"未知")
               - skills: 提取最多 8 个核心技能标签 (字符串数组)
               - ai_summary: 对候选人背景的一段简短概括 (约50字)
               - ai_analysis: 对候选人优势与劣势的深度点评 (约100字)

            简历文本：
            {extracted_text[:4000]}
            """
            
            try:
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                response_text = response.text.strip()
                parsed_data = json.loads(response_text)
            except Exception as ai_e:
                print(f"AI Parse Error: {ai_e}")
                # Check if it's a quota error (429)
                if "429" in str(ai_e) or "quota" in str(ai_e).lower():
                    parsed_data = {
                        "name": file.filename.replace('.pdf', '')[:10],
                        "job": "演示模式（API额度已满）",
                        "exp": "3-5年 / 本科",
                        "email": "demo@example.com",
                        "skills": ["API额度已满", "演示模式", "简历提取"],
                        "ai_summary": "⚠️ 当前 Gemini API 免费额度（每日20次）已耗尽，系统自动切换至离线模拟演示模式。本段文字为系统生成的模拟摘要。",
                        "ai_analysis": "由于 Google Gemini API 免费版限制，当前无法进行真实深度解析。请稍后再试或联系管理员更换 API Key。在真实环境下，此处将展示详细的候选人优劣势分析。"
                    }
                else:
                    parsed_data = {
                        "name": "AI 解析异常",
                        "job": "未能提取",
                        "exp": "未知",
                        "email": "未知",
                        "skills": ["解析失败"],
                        "ai_summary": "大模型返回内容异常或受到拦截，无法生成概括。",
                        "ai_analysis": f"异常详情：{str(ai_e)}"
                    }
        else:
            # Mock parsing logic if no API Key
            parsed_data = {
                "name": file.filename.replace('.pdf', ''),
                "job": "需配置 API Key 才能解析",
                "exp": "未知",
                "email": "未知",
                "skills": ["API未配置", "本地模拟"],
                "ai_summary": "请配置 API Key 获取概括。",
                "ai_analysis": "请配置 API Key 获取分析。"
            }

        final_job = job_title if job_title != "默认（AI自动提取）" else parsed_data.get("job", "未知")

        # 4. Save to Database
        db_candidate = models.Candidate(
            name=parsed_data.get("name", "未知"),
            job=final_job,
            stage="新投递",
            exp=parsed_data.get("exp", "未知"),
            email=parsed_data.get("email", "未知"),
            skills=parsed_data.get("skills", []),
            ai_summary=parsed_data.get("ai_summary", ""),
            ai_analysis=parsed_data.get("ai_analysis", ""),
            raw_text=extracted_text,
            pdf_path=f"/uploads/{safe_filename}"
        )
        
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)

        # 5. Save initial log
        db_log = models.CandidateLog(
            candidate_id=db_candidate.id,
            operator=operator,
            action="简历解析成功并入库"
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_candidate)

        return db_candidate

    except Exception as e:
        # cleanup file if failed and we might want to log it
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate_stage(candidate_id: int, candidate_update: schemas.CandidateUpdate, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate_update.stage is not None and candidate_update.stage != candidate.stage:
        old_stage = candidate.stage
        candidate.stage = candidate_update.stage
        
        # Log the stage change
        db_log = models.CandidateLog(
            candidate_id=candidate.id,
            operator=candidate_update.operator,
            action=f"阶段流转: {old_stage} ➔ {candidate.stage}",
            details=candidate_update.details
        )
        db.add(db_log)
    
    db.commit()
    db.refresh(candidate)
    return candidate

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Optionally delete the file if it exists
    if candidate.pdf_path:
        file_path = candidate.pdf_path.lstrip('/')
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: could not delete file {file_path}: {e}")

    db.delete(candidate)
    db.commit()
    return {"status": "success", "message": "Candidate deleted successfully"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
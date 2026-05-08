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

# Database Migration for new Job columns (Safe for SQLite)
def upgrade_db():
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            # Check if one of the new columns exists
            result = conn.execute(text("PRAGMA table_info(jobs)")).fetchall()
            columns = [row[1] for row in result]
            if "description" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN description TEXT"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN job_type VARCHAR(50) DEFAULT '全职'"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN category VARCHAR(100)"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN experience VARCHAR(50) DEFAULT '不限'"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN job_level VARCHAR(50)"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN headcount INTEGER DEFAULT 1"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN salary_range VARCHAR(50)"))
                conn.execute(text("ALTER TABLE jobs ADD COLUMN salary_months INTEGER DEFAULT 12"))
                
            c_result = conn.execute(text("PRAGMA table_info(candidates)")).fetchall()
            c_columns = [row[1] for row in c_result]
            if "match_score" not in c_columns:
                conn.execute(text("ALTER TABLE candidates ADD COLUMN match_score INTEGER"))
                conn.execute(text("ALTER TABLE candidates ADD COLUMN match_reason TEXT"))
    except Exception as e:
        print(f"Migration error (ignoring if tables just created): {e}")

upgrade_db()

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

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- API ROUTES ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Aura API is running."}

@app.get("/api/jobs", response_model=list[schemas.JobWithFunnel])
def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = db.query(models.Job).order_by(models.Job.id.desc()).offset(skip).limit(limit).all()
    result = []
    for job in jobs:
        yesterday = datetime.utcnow() - datetime.timedelta(days=1) if hasattr(datetime, 'timedelta') else datetime.now() - __import__('datetime').timedelta(days=1)
        new_resume = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage == "初筛", models.Candidate.created_at >= yesterday).count()
        screened = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage == "初筛").count()
        interviewing = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage.in_(["一面", "二面", "HR面"])).count()
        offered = db.query(models.Candidate).filter(models.Candidate.job == job.title, models.Candidate.stage == "发Offer").count()
        
        job_dict = schemas.Job.model_validate(job).model_dump()
        job_dict["funnel"] = {
            "new": new_resume,
            "screened": screened,
            "interviewing": interviewing,
            "offered": offered
        }
        result.append(job_dict)
    return result

@app.post("/api/jobs", response_model=schemas.Job)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db)):
    db_job = models.Job(**job.model_dump())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.patch("/api/jobs/{job_id}", response_model=schemas.Job)
def update_job_status(job_id: int, job_update: schemas.JobUpdate, db: Session = Depends(get_db)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job_update.status:
        db_job.status = job_update.status
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/api/candidates", response_model=list[schemas.Candidate])
def get_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        candidates = db.query(models.Candidate).order_by(models.Candidate.id.desc()).offset(skip).limit(limit).all()
        return candidates
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

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
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
            
    try:
        extracted_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
                    
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
        import re
        extracted_text = re.sub(r'[用专聘招球雪]', '', extracted_text)
        extracted_text = re.sub(r'\n\s*\n', '\n', extracted_text)

        parsed_data = {}
        
        job_info_text = ""
        if job_title != "默认（AI自动提取）":
            job_obj = db.query(models.Job).filter(models.Job.title == job_title).first()
            if job_obj:
                import re
                clean_desc = re.sub(r'<[^>]+>', '', job_obj.description or '')
                job_desc = f"{clean_desc} {job_obj.job_type or ''} {job_obj.experience or ''} {job_obj.category or ''}"
                job_info_text = f"\n【正在应聘的职位及JD】\n职位名称：{job_title}\n职位JD：{job_desc[:1000]}\n"

        if api_key:
            # 尝试的模型列表，按优先级排序
            # 使用较新且免费配额更高的型号
            candidate_models = [
                'gemini-2.5-flash-lite',
                'gemini-flash-lite-latest',
                'gemini-2.5-flash',
                'gemini-flash-latest'
            ]
            success = False
            last_error = ""

            for model_name in candidate_models:
                try:
                    print(f"Trying AI model: {model_name}...")
                    model = genai.GenerativeModel(model_name)
                    prompt = f"""
                    请作为一名资深HR数据提取专家，从以下简历文本中提取结构化信息。
                    要求：返回合法 JSON，包含 name, job, exp, email, skills(array), ai_summary, ai_analysis。
                    如果提供了【正在应聘的职位及JD】，请在提取信息后，根据简历与JD的匹配度，额外输出 match_score（0-100的整数）和 match_reason（100字左右的客观匹配维度点评）。{job_info_text}
                    简历文本：{extracted_text[:4000]}
                    """
                    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                    parsed_data = json.loads(response.text.strip())
                    success = True
                    print(f"Successfully parsed using {model_name}")
                    break # 成功则跳出循环
                except Exception as e:
                    last_error = str(e)
                    print(f"Model {model_name} failed: {e}")
                    if "429" in last_error or "quota" in last_error.lower():
                        continue # 额度满了，尝试下一个
                    elif "404" in last_error or "not found" in last_error.lower():
                        continue # 模型不存在，尝试下一个
                    else:
                        break # 其他严重错误，直接停止

            if not success:
                # 所有模型都失败后的逻辑
                if "429" in last_error or "quota" in last_error.lower():
                    parsed_data = {
                        "name": file.filename.replace('.pdf', '')[:10],
                        "job": "演示模式（API额度已满）",
                        "exp": "3-5年 / 本科",
                        "email": "demo@example.com",
                        "skills": ["所有模型额度已满", "演示模式"],
                        "ai_summary": "⚠️ 抱歉，当前所有可用的 Gemini 免费模型额度（包含 1.5/2.0 系列）均已耗尽。系统已自动切至演示模式。",
                        "ai_analysis": "Google 免费 API 每日限额较低。若需继续测试，请更换 API Key 或等待次日配额刷新。"
                    }
                else:
                    parsed_data = {"name": "AI 解析异常", "job": "错误", "exp": "未知", "email": "未知", "skills": ["解析失败"], "ai_summary": "服务响应异常", "ai_analysis": last_error}
        else:
            parsed_data = {"name": file.filename, "job": "未配置 API Key", "exp": "未知", "email": "未知", "skills": ["模拟"], "ai_summary": "未配置 Key", "ai_analysis": "未配置 Key"}

        final_job = job_title if job_title != "默认（AI自动提取）" else parsed_data.get("job", "未知")

        skills_raw = parsed_data.get("skills")
        if isinstance(skills_raw, list):
            skills_val = [str(item) for item in skills_raw]
        elif skills_raw:
            skills_val = [str(skills_raw)]
        else:
            skills_val = []

        db_candidate = models.Candidate(
            name=str(parsed_data.get("name") or "未知"),
            job=str(final_job or "未知"),
            stage="初筛",
            exp=str(parsed_data.get("exp") or "未知"),
            phone=str(parsed_data.get("phone") or "暂无"),
            email=str(parsed_data.get("email") or "暂无"),
            skills=skills_val,
            ai_summary=str(parsed_data.get("ai_summary") or ""),
            ai_analysis=str(parsed_data.get("ai_analysis") or ""),
            match_score=parsed_data.get("match_score"),
            match_reason=str(parsed_data.get("match_reason") or "") if parsed_data.get("match_reason") else None,
            raw_text=extracted_text,
            pdf_path=f"/uploads/{safe_filename}"
        )
        
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)

        db_log = models.CandidateLog(candidate_id=db_candidate.id, operator=operator, action="简历解析成功并入库")
        db.add(db_log)
        db.commit()

        return db_candidate

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate_stage(candidate_id: int, candidate_update: schemas.CandidateUpdate, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate_update.stage and candidate_update.stage != candidate.stage:
        old_stage = candidate.stage
        candidate.stage = candidate_update.stage
        db_log = models.CandidateLog(candidate_id=candidate.id, operator=candidate_update.operator, action=f"阶段流转: {old_stage} ➔ {candidate.stage}", details=candidate_update.details)
        db.add(db_log)
    
    db.commit()
    db.refresh(candidate)
    return candidate

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate.pdf_path:
        file_path = candidate.pdf_path.lstrip('/')
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass

    db.delete(candidate)
    db.commit()
    return {"status": "success"}

# --- STATIC FILES & PAGE ROUTES ---

# Mount assets and uploads
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
@app.get("/index.html")
async def read_index():
    return FileResponse('index.html')

@app.get("/candidates.html")
async def read_candidates():
    return FileResponse('candidates.html')

@app.get("/candidate-detail.html")
async def read_detail():
    return FileResponse('candidate-detail.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/interviews.html")
async def read_interviews():
    return FileResponse('interviews.html')

@app.get("/jobs.html")
async def read_jobs():
    return FileResponse('jobs.html')

@app.get("/add-candidate.html")
async def read_add_candidate():
    return FileResponse('add-candidate.html')

@app.get("/add-job.html")
async def read_add_job():
    return FileResponse('add-job.html')

@app.get("/login.html")
async def read_login():
    return FileResponse('login.html')

@app.get("/register.html")
async def read_register():
    return FileResponse('register.html')

if __name__ == "__main__":
    # In Zeabur, use the PORT environment variable
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

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
import secrets
from datetime import datetime
from dotenv import load_dotenv

from typing import Optional

import models
import schemas
import services
from database import engine, get_db

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Auto-migrate: add phone column if it doesn't exist
from sqlalchemy import text
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE candidates ADD COLUMN phone VARCHAR(50);"))
except Exception:
    pass  # column already exists or other error


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

# --- AUTH SECURITY CONFIG & TOOLS ---
import hashlib
import base64
import jwt
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "aura-ats-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{base64.b64encode(salt).decode('utf-8')}:{base64.b64encode(pwd_hash).decode('utf-8')}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt_b64, hash_b64 = hashed.split(":")
        salt = base64.b64decode(salt_b64)
        target_hash = base64.b64decode(hash_b64)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return pwd_hash == target_hash
    except Exception:
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="未提供登录凭证")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="登录凭证已失效")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录凭证已过期")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="登录凭证解析失败")
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

def init_admin_user():
    db = next(get_db())
    try:
        admin = db.query(models.User).filter(models.User.email == "hr@example.com").first()
        if not admin:
            hashed = hash_password("123456")
            db_admin = models.User(
                company="Aura Tech",
                email="hr@example.com",
                hashed_password=hashed,
                name="HR Manager",
                role="SuperAdmin"
            )
            db.add(db_admin)
            db.commit()
            print("Successfully initialized default admin user (hr@example.com / 123456)")
    except Exception as e:
        print(f"Error initializing default user: {e}")
    finally:
        db.close()

init_admin_user()

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

# --- AUTH ROUTERS ---

@app.post("/api/auth/register", response_model=schemas.TokenResponse)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="该工作邮箱已被注册")
        
    hashed = hash_password(user_data.password)
    new_user = models.User(
        company=user_data.company,
        email=user_data.email,
        hashed_password=hashed,
        name=user_data.name,
        role=user_data.role or "Admin"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": new_user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }

@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
        
    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# --- USER INVITATION ROUTERS ---

@app.post("/api/auth/invite", response_model=schemas.UserInvitationResponse)
def create_user_invitation(invite_data: schemas.UserInvitationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="没有权限执行此操作，仅限管理员")
        
    existing_user = db.query(models.User).filter(models.User.email == invite_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已注册为协同成员")
        
    existing_invite = db.query(models.UserInvitation).filter(models.UserInvitation.email == invite_data.email).first()
    if existing_invite and existing_invite.status == "pending":
        existing_invite.name = invite_data.name
        existing_invite.department = invite_data.department
        existing_invite.role = invite_data.role
        existing_invite.token = secrets.token_hex(24)
        existing_invite.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_invite)
        invitation = existing_invite
    else:
        if existing_invite:
            db.delete(existing_invite)
            db.commit()
            
        token = secrets.token_hex(24)
        invitation = models.UserInvitation(
            email=invite_data.email,
            name=invite_data.name,
            department=invite_data.department,
            role=invite_data.role,
            token=token,
            status="pending"
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)

    invite_link = f"https://aura-ats.zeabur.app/register.html?invite_token={invitation.token}"
    company_name = current_user.company or "Aura Tech"
    
    services.EmailService.send_user_invitation(
        to_email=invitation.email,
        invite_link=invite_link,
        inviter_name=current_user.name,
        company_name=company_name
    )
    
    return invitation

@app.get("/api/auth/invite", response_model=list[schemas.UserInvitationResponse])
def get_user_invitations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="没有权限执行此操作")
    return db.query(models.UserInvitation).order_by(models.UserInvitation.id.desc()).all()

@app.get("/api/auth/invite/detail/{token}", response_model=schemas.UserInvitationResponse)
def get_invitation_detail(token: str, db: Session = Depends(get_db)):
    invite = db.query(models.UserInvitation).filter(models.UserInvitation.token == token).first()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=400, detail="邀请链接无效或已过期")
    return invite

@app.post("/api/auth/register-by-invite", response_model=schemas.TokenResponse)
def register_by_invite(reg_data: schemas.RegisterByInvite, db: Session = Depends(get_db)):
    invite = db.query(models.UserInvitation).filter(models.UserInvitation.token == reg_data.token).first()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=400, detail="激活链接失效，注册失败")
        
    existing_user = db.query(models.User).filter(models.User.email == invite.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
        
    hashed = hash_password(reg_data.password)
    new_user = models.User(
        company="Aura Tech",
        email=invite.email,
        hashed_password=hashed,
        name=reg_data.name or invite.name,
        role=invite.role
    )
    db.add(new_user)
    invite.status = "accepted"
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": new_user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }



@app.get("/api/jobs", response_model=list[schemas.JobWithFunnel])
def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
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
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_job = models.Job(**job.model_dump())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/api/jobs/{job_id}", response_model=schemas.Job)
def get_job(job_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

@app.patch("/api/jobs/{job_id}", response_model=schemas.Job)
def update_job_status(job_id: int, job_update: schemas.JobUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job_update.status:
        db_job.status = job_update.status
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/api/candidates", response_model=list[schemas.Candidate])
def get_candidates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        candidates = db.query(models.Candidate).order_by(models.Candidate.id.desc()).offset(skip).limit(limit).all()
        return candidates
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def get_candidate(candidate_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@app.post("/api/parse-resume", response_model=schemas.Candidate)
async def parse_resume(file: UploadFile = File(...), job_title: str = Form("默认（AI自动提取）"), operator: str = Form("系统"), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
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
                    要求：返回合法 JSON，包含 name(请准确提取候选人本人的真实姓名，不要提取成文件名、其他称呼或乱码), job, exp(仅提取最高学历，如"本科"、"硕士"等，不要包含工作年限), phone(请仔细提取手机号，通常为11位数字), email, skills(array), ai_summary, ai_analysis。
                    在编写 ai_analysis 时，请务必包含以下三个维度的结构化点评（请只使用纯文本和 HTML 的 <br> 换行，绝对不要使用 Markdown 语法如 **加粗** 或 # 标题）：
                    ✅ 亮点（候选人优势）；<br>
                    ⚠️ 风险（劣势项或经验短板）；<br>
                    🎯 面试建议（结合职位描述，提示需面试官重点关注或追问的维度）。
                    如果提供了【正在应聘的职位及JD】，请在提取信息和编写点评时，紧密结合该 JD要求，并额外输出 match_score（0-100的整数）和 match_reason（简短的综合匹配度总结）。{job_info_text}
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

        db_log = models.CandidateLog(candidate_id=db_candidate.id, operator=current_user.name, action="简历解析成功并入库")
        db.add(db_log)
        db.commit()

        return db_candidate

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/candidates/{candidate_id}", response_model=schemas.Candidate)
def update_candidate_stage(candidate_id: int, candidate_update: schemas.CandidateUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if candidate_update.stage and candidate_update.stage != candidate.stage:
        old_stage = candidate.stage
        candidate.stage = candidate_update.stage
        # 使用当前登录的真实用户记录修改日志
        operator_name = current_user.name if current_user else candidate_update.operator
        db_log = models.CandidateLog(candidate_id=candidate.id, operator=operator_name, action=f"阶段流转: {old_stage} ➔ {candidate.stage}", details=candidate_update.details)
        db.add(db_log)
    
    db.commit()
    db.refresh(candidate)
    return candidate

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
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
    return FileResponse('index.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/candidates.html")
async def read_candidates():
    return FileResponse('candidates.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
@app.get("/talent-pool.html")
async def read_talent_pool():
    return FileResponse('talent-pool.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/candidate-detail.html")
async def read_detail():
    return FileResponse('candidate-detail.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/interviews.html")
async def read_interviews():
    return FileResponse('interviews.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/jobs.html")
async def read_jobs():
    return FileResponse('jobs.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/add-candidate.html")
async def read_add_candidate():
    return FileResponse('add-candidate.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/add-job.html")
async def read_add_job():
    return FileResponse('add-job.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/login.html")
async def read_login():
    return FileResponse('login.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/register.html")
async def read_register():
    return FileResponse('register.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/settings.html")
async def read_settings():
    return FileResponse('settings.html', headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# --- System Settings APIs ---

@app.get("/api/settings/departments", response_model=list[schemas.Department])
def get_departments(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Department).all()

@app.post("/api/settings/departments", response_model=schemas.Department)
def create_department(item: schemas.DepartmentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_item = models.Department(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/departments/{item_id}")
def delete_department(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.Department).filter(models.Department.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/interviewers", response_model=list[schemas.Interviewer])
def get_interviewers(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Interviewer).all()

@app.post("/api/settings/interviewers", response_model=schemas.Interviewer)
def create_interviewer(item: schemas.InterviewerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_item = models.Interviewer(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/interviewers/{item_id}")
def delete_interviewer(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.Interviewer).filter(models.Interviewer.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/locations", response_model=list[schemas.Location])
def get_locations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Location).all()

@app.post("/api/settings/locations", response_model=schemas.Location)
def create_location(item: schemas.LocationCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_item = models.Location(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/locations/{item_id}")
def delete_location(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.Location).filter(models.Location.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/interview-processes", response_model=list[schemas.InterviewProcess])
def get_interview_processes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.InterviewProcess).all()

@app.post("/api/settings/interview-processes", response_model=schemas.InterviewProcess)
def create_interview_process(item: schemas.InterviewProcessCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_item = models.InterviewProcess(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/interview-processes/{item_id}")
def delete_interview_process(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.InterviewProcess).filter(models.InterviewProcess.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/categories", response_model=list[schemas.JobCategory])
def get_categories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.JobCategory).all()

@app.post("/api/settings/categories", response_model=schemas.JobCategory)
def create_category(item: schemas.JobCategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_item = models.JobCategory(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/settings/categories/{item_id}")
def delete_category(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.JobCategory).filter(models.JobCategory.id == item_id).delete()
    db.commit()
    return {"ok": True}

@app.get("/api/settings/email-templates", response_model=list[schemas.EmailTemplate])
def get_email_templates(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.EmailTemplate).all()

@app.get("/api/settings/feedback-templates", response_model=list[schemas.FeedbackTemplate])
def get_feedback_templates(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.FeedbackTemplate).all()

@app.get("/api/calendar/freebusy")
def get_freebusy(interviewer: str, date: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return services.FeishuCalendarService.get_freebusy(interviewer, date, db)

@app.post("/api/interviews", response_model=schemas.Interview)
def create_interview(item: schemas.InterviewCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_item = models.Interview(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    # Send email and create event
    candidate = db.query(models.Candidate).filter(models.Candidate.id == item.candidate_id).first()
    if candidate:
        template = db.query(models.EmailTemplate).first() # Simplify: get first template
        if template:
            content = template.content.replace("{candidate_name}", candidate.name) \
                                      .replace("{job_title}", item.job_title) \
                                      .replace("{interview_time}", str(item.start_time)) \
                                      .replace("{location}", item.location)
            subject = template.subject.replace("{job_title}", item.job_title)
            services.EmailService.send_interview_invitation(candidate.email or "demo@example.com", subject, content)
            
    services.FeishuCalendarService.create_event(item.interviewer_name, item.start_time, item.end_time, "面试安排", "...")
    
    return db_item

@app.get("/api/interviews", response_model=list[schemas.Interview])
def get_interviews(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Interview).all()

@app.patch("/api/interviews/{interview_id}/feedback", response_model=schemas.Interview)
def submit_feedback(interview_id: int, feedback: schemas.InterviewUpdateFeedback, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    interview.feedback_result = feedback.feedback_result
    interview.feedback_text = feedback.feedback_text
    interview.status = "已完成" # Automatically set status to completed
    db.commit()
    db.refresh(interview)
    return interview

# --- Workbench Dashboard API ---

@app.get("/api/workbench/dashboard", response_model=schemas.DashboardSummary)
def get_dashboard_data(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    role = current_user.role
    name = current_user.name

    # 1. 统计数据 (Stats)
    active_jobs = db.query(models.Job).filter(models.Job.status == "热招中").count()
    
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    week_candidates = db.query(models.Candidate).filter(models.Candidate.created_at >= seven_days_ago).count()
    
    pending_interviews = db.query(models.Interview).filter(models.Interview.status == "已安排").count()
    
    high_score_alerts = db.query(models.Candidate).filter(models.Candidate.match_score > 85).count()
    
    stats = [
        {"label": "活跃职位", "value": active_jobs, "change": "+2", "icon": "briefcase"},
        {"label": "本周候选人", "value": week_candidates, "change": "+15%", "icon": "users"},
        {"label": "待安排面试", "value": pending_interviews, "change": "今日 4 场", "icon": "calendar"},
        {"label": "待处理预警", "value": high_score_alerts, "change": "高分简历", "icon": "alert-circle"}
    ]
    
    # 2. 待办事项 (Todos)
    todos = []
    
    # 面试官视角：仅看自己的面试
    if role == "Interviewer":
        my_interviews = db.query(models.Interview).filter(
            models.Interview.interviewer_name == name,
            models.Interview.status == "已安排"
        ).order_by(models.Interview.start_time.asc()).limit(5).all()
        
        for idx, itv in enumerate(my_interviews):
            todos.append({
                "id": itv.id,
                "type": "interview",
                "title": f"面试: {itv.job_title}",
                "time": itv.start_time.strftime("%m-%d %H:%M"),
                "status": "已预约",
                "candidate_id": itv.candidate_id
            })
    else:
        # HR/管理员视角：看高分预警
        alerts = db.query(models.Candidate).filter(
            models.Candidate.match_score > 85
        ).order_by(models.Candidate.match_score.desc()).limit(5).all()
        
        for c in alerts:
            todos.append({
                "id": c.id,
                "type": "resume_alert",
                "title": f"高分预警: {c.name} ({c.match_score}分)",
                "time": "刚刚",
                "status": "待查看",
                "candidate_id": c.id
            })
            
    # 3. 最近动态 (Activities)
    activities = []
    
    if role == "Interviewer":
        activities = [
            {
                "id": 1,
                "content": "HR <strong style='color:var(--text-primary)'>Ethan</strong> 将你添加为 <strong>林慕风</strong> 的初面面试官。",
                "time": "10 分钟前",
                "icon": "user-plus",
                "color": "#007AFF",
                "candidate_id": 1
            },
            {
                "id": 2,
                "content": "HR 更新了你明天下午的面试日程：<strong>赵雷</strong> (前端开发)。",
                "time": "2 小时前",
                "icon": "calendar",
                "color": "#FF9500",
                "candidate_id": 2
            }
        ]
    else: # HR/Admin
        activities = [
            {
                "id": 3,
                "content": "AI 已成功解析 <strong>林慕风</strong> 的简历，并提取了核心亮点。",
                "time": "10 分钟前",
                "icon": "sparkles",
                "color": "#AF52DE",
                "candidate_id": 1
            },
            {
                "id": 4,
                "content": "<strong>李思齐</strong> (面试官) 刚刚提交了 <strong>赵雷</strong> 的面试反馈：<span style='color:#34C759;font-weight:600'>通过</span>。",
                "time": "1 小时前",
                "icon": "check-circle",
                "color": "#34C759",
                "candidate_id": 2
            },
            {
                "id": 5,
                "content": "候选人 <strong>王浩然</strong> 已被标记为淘汰。",
                "time": "3 小时前",
                "icon": "x-circle",
                "color": "#FF3B30",
                "candidate_id": 3
            },
            {
                "id": 6,
                "content": "新职位 <strong>[高级算法工程师]</strong> 已成功发布并上线。",
                "time": "昨天",
                "icon": "briefcase",
                "color": "#007AFF",
                "candidate_id": None
            }
        ]
        
    return {
        "stats": stats,
        "todos": todos,
        "activities": activities
    }

if __name__ == "__main__":
    # In Zeabur, use the PORT environment variable
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

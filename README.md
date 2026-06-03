# 🚀 Aura 灵犀招聘系统 (Aura-ATS)

Aura 是一款基于大语言模型 (LLM) 驱动的现代化智能招聘管理系统 (ATS)。其界面融合了现代、简洁的 **Apple 设计哲学**（如毛玻璃拟态、Bento Grid 磁贴布局和微交互动效），提供卓越的 SaaS 级 UI/UX 体验。

---

## 🛠️ 技术栈与架构
*   **后端**：`Python (FastAPI)` + `SQLAlchemy (ORM)` + `SQLite / MySQL`
*   **AI 简历解析**：`Google Gemini API` (具备轻量模型自适应轮询与脱机演示降级兜底功能) + `pdfplumber`
*   **安全与鉴权**：
    *   **JWT 身份令牌**：采用 `pyjwt` 生成与校验 Token，用于全站 API 越权拦截与权限隔离。
    *   **密码哈希安全存储**：采用 Python 内置标准库 `PBKDF2-HMAC-SHA256` 进行强哈希存储，确保数据安全并免去 C 语言库编译依赖。
*   **前端**：原生 `HTML` + `Vanilla CSS` + `JavaScript` (零框架、极速轻量)

---

## 📦 快速本地启动

### 1. 克隆/打开项目并安装依赖
我们新增了 `pyjwt` 依赖。请在终端执行以下命令进行依赖更新安装：
```bash
# 激活您的虚拟环境 (如果有的话，例如 venv)
source venv/bin/activate

# 安装最新依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
在项目根目录下创建 `.env` 文件，并配置您的 Gemini API 凭证：
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. 运行本地开发服务器
启动 FastAPI 异步服务器：
```bash
python main.py
```
默认服务将运行在 `http://localhost:8000`。

---

## 👤 初始演示账号
系统在初次启动并初始化数据库时，会自动生成一个用于测试和演示的默认管理员账号：
*   **登录邮箱**：`hr@example.com`
*   **默认密码**：`123456`
*   **权限级别**：超级管理员 (SuperAdmin)

---

## 🗺️ 项目演进历史与蓝图
*   详细的日常开发决策与版本里程碑见：[Progress_Newton-(牛顿).md](file:///Users/caoyixiong/AI%20Project/Aura/Progress_Newton-%28%E7%89%9B%E9%A1%BF%29.md)。
*   V2.6 -> V3.0 的生产化迁移蓝图见：[Aura_V2.6_至_V3.0_生产化演进蓝图.md](file:///Users/caoyixiong/AI%20Project/Aura/%E8%BF%9B%E5%BA%A6%E6%B1%87%E6%8A%A5/Aura_V2.6_%E8%87%B3_V3.0_%E7%94%9F%E4%BA%A7%E5%8C%96%E6%BC%94%E8%BF%9B%E8%93%9D%E5%9B%BE.md)。

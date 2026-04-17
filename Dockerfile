# 使用官方的轻量级 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目到容器中
COPY . .

# 暴露 8000 端口（本地默认）
EXPOSE 8000

# 启动 FastAPI 服务，允许云平台通过环境变量 PORT 动态分配端口
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
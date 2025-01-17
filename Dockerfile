# 使用官方 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码和静态资源
COPY . .

# 暴露端口
EXPOSE 3355

# 启动服务
CMD ["python", "run_server.py"]
# 使用官方 Python 镜像（移除硬编码的 --platform）
FROM python:3.9-slim

# 设置时区为上海（与本地环境一致）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 安装系统依赖
RUN test -f /etc/apt/sources.list || echo "deb http://deb.debian.org/debian stable main" > /etc/apt/sources.list && \
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    apt-get update --fix-missing && \
    apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 禁用 Python 输出缓冲
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 3355

# 启动服务
CMD ["python", "-u", "run_server.py"]

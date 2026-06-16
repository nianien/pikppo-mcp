FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 先装依赖（独立缓存层：lock 不变则跳过），再装项目本体
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# 云端默认关闭 Host 白名单（认证由 MCP_AUTH_TOKEN 兜底，缺失时应用拒绝启动），部署时注入 DB_URL
ENV MCP_ALLOWED_HOSTS=*

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["python", "-m", "app", "--host", "0.0.0.0"]

#!/usr/bin/env bash
# 部署 pikppo-mcp 到 Cloud Run，并用 Cloud Run domain mapping 绑定自定义域名（无 LB）
#
# Usage: bash scripts/deploy-gcp.sh [--no-build]
#   无参数      Cloud Build 构建新镜像 + 部署（默认）
#   --no-build  跳过构建，复用已有镜像重新部署
#
# 前置: gcloud 已登录；.env 中已配置 DB_URL（Neon 连接串）
# 流量链路: mcp.pikppo.com (CNAME/A → ghs.googlehosted.com) → Cloud Run domain mapping → Cloud Run
# 证书: domain mapping 自动签发/续期 Google 托管证书，无需自管
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# ── 配置 ──────────────────────────────────────────────────
PROJECT="${PROJECT_ID:-pikppo}"
REGION="${REGION:-asia-southeast1}"      # 与 Neon ap-southeast-1 同城（新加坡）
SERVICE="pikppo-mcp"
DOMAIN="${DOMAIN:-mcp.pikppo.com}"
REPO="pikppo-mcp"
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:latest"

SECRET_DB="pikppo-db-url"
SECRET_TOKEN="pikppo-auth-token"

log()  { echo "==> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

# ── 参数 ──────────────────────────────────────────────────
BUILD=true
for arg in "$@"; do
  case "$arg" in
    --no-build) BUILD=false ;;
    --help|-h)  sed -n '2,10p' "$0"; exit 0 ;;
    *)          fail "Unknown argument: $arg" ;;
  esac
done

# ── 前置检查 ──────────────────────────────────────────────
command -v gcloud >/dev/null || fail "gcloud CLI not installed"
gcloud auth print-access-token &>/dev/null || fail "gcloud 未登录，先执行 gcloud auth login"
log "项目: $PROJECT | 区域: $REGION | 域名: $DOMAIN"

log "启用所需 API"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com \
  --project "$PROJECT"

# ── 构建镜像 ─────────────────────────────────────────────
if ! gcloud artifacts repositories describe "$REPO" --location "$REGION" --project "$PROJECT" >/dev/null 2>&1; then
  log "创建 Artifact Registry 仓库 $REPO"
  gcloud artifacts repositories create "$REPO" --repository-format=docker \
    --location "$REGION" --project "$PROJECT"
fi

if $BUILD; then
  log "Cloud Build 构建镜像..."
  gcloud builds submit --config=scripts/cloudbuild.yaml \
    --substitutions=_IMAGE_URL="$IMAGE_URL" --project "$PROJECT" .
fi

# ── Secrets ──────────────────────────────────────────────
ensure_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" --project "$PROJECT" >/dev/null 2>&1; then
    log "secret $name 已存在，跳过"
  else
    printf %s "$value" | gcloud secrets create "$name" --data-file=- --project "$PROJECT"
    log "secret $name 已创建"
  fi
}

log "准备 secrets"
DB_URL_VALUE="$(grep -E '^DB_URL=' .env 2>/dev/null | head -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//')"
if [[ -z "$DB_URL_VALUE" ]] && ! gcloud secrets describe "$SECRET_DB" --project "$PROJECT" >/dev/null 2>&1; then
  fail ".env 中没有 DB_URL，且 secret $SECRET_DB 不存在"
fi
[[ -n "$DB_URL_VALUE" ]] && ensure_secret "$SECRET_DB" "$DB_URL_VALUE"

if ! gcloud secrets describe "$SECRET_TOKEN" --project "$PROJECT" >/dev/null 2>&1; then
  AUTH_TOKEN="$(openssl rand -hex 32)"
  ensure_secret "$SECRET_TOKEN" "$AUTH_TOKEN"
  log "已生成认证 token（Flutter 端需配置同一值）: $AUTH_TOKEN"
fi

# 专用最小权限运行 SA：仅持有两个 secret 的资源级读权限，无任何项目级角色
RUNTIME_SA="pikppo-mcp@${PROJECT}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$RUNTIME_SA" --project "$PROJECT" >/dev/null 2>&1; then
  log "创建专用运行 SA: $RUNTIME_SA"
  gcloud iam service-accounts create pikppo-mcp \
    --display-name "pikppo-mcp Cloud Run runtime" --project "$PROJECT"
fi
for s in "$SECRET_DB" "$SECRET_TOKEN"; do
  gcloud secrets add-iam-policy-binding "$s" \
    --member "serviceAccount:$RUNTIME_SA" \
    --role roles/secretmanager.secretAccessor \
    --project "$PROJECT" >/dev/null
done

# ── Cloud Run ────────────────────────────────────────────
log "部署 Cloud Run 服务"
# domain mapping 走公网入口，ingress 须为 all；公网安全由应用层 MCP_AUTH_TOKEN 承担（fail-closed）
gcloud run deploy "$SERVICE" \
  --image "$IMAGE_URL" \
  --project "$PROJECT" \
  --region "$REGION" \
  --service-account "$RUNTIME_SA" \
  --allow-unauthenticated \
  --ingress all \
  --set-env-vars "MCP_ALLOWED_HOSTS=*" \
  --set-secrets "DB_URL=${SECRET_DB}:latest,MCP_AUTH_TOKEN=${SECRET_TOKEN}:latest" \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --min-instances 0 \
  --max-instances 5 \
  --quiet

# ── 绑定自定义域名（Cloud Run domain mapping，幂等）────────
log "绑定域名: Cloud Run domain mapping"
if ! gcloud beta run domain-mappings describe --domain "$DOMAIN" \
  --region "$REGION" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud beta run domain-mappings create \
    --service "$SERVICE" --domain "$DOMAIN" \
    --region "$REGION" --project "$PROJECT"
fi

# ── 输出 ─────────────────────────────────────────────────
echo ""
log "部署完成"
echo "    DNS:      为 $DOMAIN 添加 Google 给出的记录（多数为 CNAME → ghs.googlehosted.com）："
gcloud beta run domain-mappings describe --domain "$DOMAIN" \
  --region "$REGION" --project "$PROJECT" \
  --format 'value(status.resourceRecords[].rrdata)' | sed 's/^/                /'
echo "    证书状态: DNS 生效后 domain mapping 自动签发 Google 托管证书（约 15-60 分钟）"
echo "    查看状态: gcloud beta run domain-mappings describe --domain $DOMAIN --region $REGION --project $PROJECT"
echo "    MCP 地址: https://${DOMAIN}/mcp"
echo "    请求头:   Authorization: Bearer <token>"
echo "    取 token: gcloud secrets versions access latest --secret $SECRET_TOKEN --project $PROJECT"

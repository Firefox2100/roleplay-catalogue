# 部署

角色扮演资源库提供预构建的 Docker 镜像，也可以从源码部署。有两种部署模式：

| 模式 | 说明 |
|---|---|
| **全-in-one** (Docker Compose) | 单一 `ghcr.io/Firefox2100/roleplay-catalogue` 镜像内置 Nginx + Uvicorn；只需外部 MongoDB 和 MinIO。 |
| **拆分** | 独立的 FastAPI 后端位于 `/api` 路径 + 任意 SPA 宿主（反向代理、CDN、S3 存储桶）。你自行构建前端并选择 Uvicorn 的运行位置。 |

---

## 前置要求

- **Python** ≥ 3.12
- **Node.js** ≥ 18（用于构建前端）
- **MongoDB** 以 **副本集** 模式运行（单节点副本集即可用于本地或小规模部署）——**必须**，因为应用使用多文档事务。
- **S3 兼容存储**（MinIO、AWS S3、Cloudflare R2 等）——用于上传角色卡、背景书、预设、图片和世界数据包。

---

## 方案一 — Docker Compose（推荐）

提供的 `compose.yaml` 启动四个服务：

| 服务 | 作用 | Docker 镜像 |
|---|---|---|
| `catalogue` | Nginx（端口 8080）将 `/api/` 代理到 9798 端口的 Uvicorn；提供 SPA。 | `ghcr.io/Firefox2100/roleplay-catalogue:latest` |
| `mongodb` | MongoDB Community Server，单节点副本集 `rs0`。 | `mongodb/mongodb-community-server:latest` |
| `mongodb-search`（mongot） | MongoDB Community Search，提供全文和向量索引。 | `mongodb/mongodb-community-search:latest` |
| `minio` | 9000 端口的 S3 兼容对象存储（控制台在 9001）。 | `minio/minio:latest` |

两个一次性初始化容器（`mongodb-init`、`minio-init`）在 MongoDB 和 MinIO 健康后各运行一次：

- `mongodb-init` 执行 `init-mongodb.sh`（配置副本集和 mongot 搜索索引）。
- `minio-init` 创建在 `RC_S3_BUCKET` 中配置的 S3 存储桶。

### 操作步骤

```sh
# 1. 复制并编辑环境文件
cp example.env .env
# 至少编辑 RC_SESSION_SECRET、MONGOT_PASSWORD、RC_PUBLIC_BASE_URL

# 2. 启动
docker compose up -d

# 3. 验证
docker compose ps           # 所有容器应显示 Up 状态
docker compose logs -f catalogue   # 跟踪应用日志
```

### 容器内的 Nginx

`catalogue` 镜像内嵌了 Nginx 配置（构建时在 `deploy/nginx.conf` 中定义模板）。它执行：

- `location /api/` → 代理到 `127.0.0.1:9798` 上的 Uvicorn，
  设置 `proxy_read_timeout 300s` 且禁用客户端 body 缓冲。
- `location /` → SPA 回退到 `index.html`，支持客户端路由。
- `client_max_body_size 21m` —— 高于默认值 1m，确保大图片上传成功。
  可通过自定义镜像或编辑渲染后的 Nginx 配置调整。

容器暴露 **端口 8080**（从 `CATALOGUE_PORT` 映射）。所有浏览器连接
8080 端口；`/api/*` 请求通过 Nginx 透明转发到后端。

### 自定义 compose 堆栈

你可以通过 `.env` 文件或 `catalogue` 服务的环境变量覆盖任何 `compose.yaml` 值。
`CATALOGUE_PORT` 变量控制映射到容器的宿主机端口；`RC_SESSION_SECRET`、
`MONGOT_PASSWORD`、`RC_PUBLIC_BASE_URL`、SMTP 设置和 S3 凭证在
首次启动前从 `.env` 填充。

---

## 方案二 — 从源码部署拆分模式

当你希望将 SPA 前端和 Python 后端解耦时使用此方案（例如你已有 CDN，或者在
不同机器上部署前后端）。

### 2.1 构建前端

```sh
cd frontend
npm install
npm run build          # 生成 frontend/dist/
```

将 `frontend/dist/` 复制到你的托管目标：

| 托管方式 | 方法 |
|---|---|
| **Nginx（独立）** | `sudo cp -r dist/* /var/www/roleplay-catalogue/` 并通过 Nginx 在 `/` 提供。启用 SPA 回退（`try_files $uri $uri/ /index.html`）。 |
| **Cloudflare Pages / Vercel / 任意 CDN** | 将 `dist/` 目录部署为静态站点。确保 `index.html` 是单页回退。 |
| **S3 + CloudFront** | 将 `dist/` 内容上传到配置为静态站点的 S3 存储桶，CloudFront 指向它并启用 SPA 回退到 `index.html`。 |

### 2.2 运行后端

```sh
cd src/roleplay_catalogue        # 从仓库根目录

# 创建并激活虚拟环境（Python 3.12）
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 复制并编辑环境文件
cp ../example.env .env           # 或将 .env 放在 uvicorn 可以找到它的位置
# 拆分模式下 RC_FRONTEND_DIST_PATH=""（不需要设置）
# 设置 RC_API_PREFIX=/api        # 使用独立代理时可留空
```

通过直接运行或用你喜欢的进程管理器启动 Uvicorn：

```sh
# 直接运行（开发）
# Uvicorn 绑定到 RC_APP_HOST:RC_APP_PORT（默认 127.0.0.1:9798）
uvicorn roleplay_catalogue.main:app --host 0.0.0.0 --port 9798

# 生产环境 — 通过 systemd、supervisord、docker、k8s 等运行
```

或者在轻量容器中运行：

```sh
docker run --rm -p 9798:9798 \
  -e RC_MONGODB_HOST=mongodb \
  -e RC_S3_ENDPOINT_URL=http://minio:9000 \
  -e RC_API_PREFIX=/api \
  ghcr.io/fk2100/fastapi-uvicorn:latest \
  bash -c "pip install roleplay-catalogue && uvicorn roleplay_catalogue.main:app --host 0.0.0.0 --port 9798"
```

### 2.3 前端 ↔ 后端连接

前端和后端通过 **API 前缀** 路径通信：

- 后端设置 `RC_API_PREFIX` 为 `/api`。
- 前端的基础 URL 必须包含此前缀：浏览器请求
  `https://example.com/api/resources` 到 SPA（由 CDN/Nginx 提供），
  SPA 发送 XHR/fetch 请求到 `/api/resources`。
- 你的 **反向代理** 必须将 `https://your-domain/api/*` 转发到后端
  （在自己的主机和端口上运行）。Apache 示例：

  ```apache
  ProxyPass /api http://backend-host:9798/
  ProxyPassReverse /api http://backend-host:9798/
  ```

- 或 Nginx：

  ```nginx
  location /api/ {
      proxy_pass http://backend-host:9798/;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
  }
  ```

> [!IMPORTANT]
> 后端必须相对于公共 URL 在 `/api` 路径下提供。如果后端位于
> `https://backend.example.com`，你想让它通过
> `https://example.com/api` 对外提供，则前置反向代理或负载均衡器
> 必须重写路径。Uvicorn 通过 `proxy_pass` 指向 `http://backend/`
> （而非 `http://backend/api/`）时默认剥离一级路径。

### 2.4 所需环境变量（拆分模式）

以下是**必须设置**的变量；其余变量取自 `example.env` 默认值。

| 变量 | 示例值 | 说明 |
|---|---|---|
| `RC_SESSION_SECRET` | `a3f1b7c9d2e4...` | 最少 32 字节 |
| `RC_MONGODB_HOST` | `10.0.1.5` | 主机名或副本集种子地址 |
| `RC_MONGODB_REPLICA_SET` | `rs0` | 必须与 `mongod --replSet` 匹配 |
| `RC_S3_ENDPOINT_URL` | `https://my-bucket.r2.cloudflarestorage.com` | 末尾无斜杠 |
| `RC_S3_REGION` | `auto` | 部分提供商要求此字面值 |
| `RC_S3_ACCESS_KEY_ID` | `AKIA...` | |
| `RC_S3_SECRET_ACCESS_KEY` | `abc123...` | |
| `RC_PUBLIC_BASE_URL` | `https://roleplay.example.com` | 浏览器端 URL；用于邮件链接 |
| `RC_API_PREFIX` | `/api` | 必须与公共 URL 下的路径匹配 |
| `RC_SMTP_HOST` | `smtp.gmail.com` | 为空字符串则禁用邮件 |
| `RC_SMTP_PORT` | `587` | 配合 `RC_SMTP_START_TLS=true` |
| `RC_SMTP_USERNAME` | `you@example.com` | |
| `RC_SMTP_PASSWORD` | `app-key` | |

---

## 反向代理注意事项

当运行在 HTTPS 反向代理后面（Traefik、Caddy、HAProxy、Cloudflare
等）时，代理必须从 `/api/*` **剥离一个前导斜杠**后转发到 Uvicorn，
因为后端挂载在 `RC_API_PREFIX=/api` 下。有些代理将
`/api/resources` → `http://backend:9798/api/resources` 转发（双重
`/api`）；确保 `ProxyPass` 或 `location` 块映射到
`http://backend:9798/`（而非 `/api/`）。

---

## 部署检查清单

- [ ] 已设置 `RC_SESSION_SECRET`（≥ 32 个随机字符）。
- [ ] MongoDB 是 **副本集**（`--replSet` 标志与 `RC_MONGODB_REPLICA_SET` 匹配）。
- [ ] S3 存储桶已存在且凭证正确（拆分模式下）。
- [ ] `RC_PUBLIC_BASE_URL` 匹配用户导航的公共域名 + 协议。
- [ ] 反向代理将 `/api/*` → `http://backend-host/api/`（剥离一级路径）。
- [ ] 已设置 `RC_SMTP_HOST`（或留空禁用邮件，如果激活是可选的）。
- [ ] 安全头：启用 HTTPS -only 前提下已将 `RC_HSTS_MAX_AGE` 设为正值。
- [ ] 已检查 `RC_CONTENT_SECURITY_POLICY` 与任何外部资产或第三方集
  成的兼容性（例如加载角色卡的 SillyTavern 实例）。

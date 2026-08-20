# 配置选项

角色扮演资源库的所有配置均通过环境变量完成。每个变量都使用 `RC_` 前缀（外部服务如 MongoDB、MinIO 等除外）。完整参考是仓库根目录下的 `example.env`——首次使用前请将其复制为 `.env`。

所有配置在启动时通过 [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) 模型进行验证。无效值会导致容器启动失败并输出错误信息。

## Docker Compose 变量

这些变量来自 `compose.yaml`，影响 Docker 环境。它们覆盖 `.env` 中的值或从中读取。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CATALOGUE_PORT` | `8080` | catalogue Web 界面映射到宿主机的主机端口。 |
| `NGINX_HSTS_HEADER` | 空 | 注入到 Nginx 响应中的完整 HSTS 头（例如 `max-age=31536000; includeSubDomains`）。仅在 Docker 模式下生效。 |
| `NGINX_CONTENT_SECURITY_POLICY` | 见 `example.env` | Nginx 响应的 CSP 头覆盖值。仅在 Docker 模式下生效。 |

## 应用服务器

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_APP_HOST` | `127.0.0.1` | Uvicorn 工作进程绑定的主机地址。 |
| `RC_APP_PORT` | `9798` | Uvicorn 工作进程监听的端口。 |
| `RC_LOGGING_LEVEL` | `INFO` | Python 日志级别（`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`）。 |

## API 前缀

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_API_PREFIX` | 空 | 添加到所有 FastAPI 路由的前缀。当前端在 `/` 挂载 SPA 且将 `/api/*` 请求转发到后端时设为 `/api`。裸部署时留空。 |
| `RC_FRONTEND_DIST_PATH` | 空 | 已构建的 Vite `dist/` 目录的绝对路径。设置后 FastAPI 从 `/` 提供 SPA 并通过客户端路由回退。外部反向代理或 CDN 提供前端时留空。 |

## MongoDB

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_MONGODB_HOST` | `127.0.0.1` | MongoDB 主机名（副本集可用逗号分隔多个主机）。 |
| `RC_MONGODB_PORT` | `27017` | MongoDB 端口。 |
| `RC_MONGODB_NAME` | `roleplay-catalogue` | 数据库名称。 |
| `RC_MONGODB_DIRECT_CONNECTION` | `false` | 如果为 `true`，跳过副本集发现机制，仅连接 `RC_MONGODB_HOST` 列出的主机。事务要求使用副本集模式。 |
| `RC_MONGODB_REPLICA_SET` | `rs0` | 副本集名称。`mongod` 命令行 `--replSet` 标志的值必须与此一致。留空表示使用独立 MongoDB 连接。 |
| `RC_MONGODB_USERNAME` | 空 | MongoDB 认证的可选用户名。与 `RC_MONGODB_PASSWORD` 都留空表示不使用认证连接。 |
| `RC_MONGODB_PASSWORD` | 空 | MongoDB 认证的可选密码，与 `RC_MONGODB_USERNAME` 搭配使用。认证数据库（`authSource`）为 `RC_MONGODB_NAME`。 |

MongoDB 事务对原子多文档操作（例如在一次写入中创建资源、其草稿数据和索引搜索）是必需的。`compose.yaml` 提供的单节点副本集足以用于开发环境。

## S3 兼容存储

应用使用 S3 兼容存储来保存资源工件（角色卡文件、背景书文件、预设文件、图片和世界模拟数据包）。任何 S3 API 实现均可使用（AWS S3、MinIO、Cloudflare R2 等）。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_S3_ENDPOINT_URL` | `http://127.0.0.1:9000` | S3 API 端点 URL。生产环境设为 `https://s3.amazonaws.com` 或你的提供商端点。 |
| `RC_S3_REGION` | `us-east-1` | AWS 区域标识符。部分提供商要求为空字符串。 |
| `RC_S3_ACCESS_KEY_ID` | `minioadmin` | S3 访问密钥。 |
| `RC_S3_SECRET_ACCESS_KEY` | `minioadmin` | S3 密钥。 |
| `RC_S3_BUCKET` | `roleplay-catalogue` | S3 存储桶名称。Docker Compose 初始化任务会自动创建。外部服务请确保已存在。 |
| `RC_IMAGE_MAX_BYTES` | `20971520`（20 MiB） | 图片上传的最大大小（封面图、独立图片）。 |
| `RC_WORLD_BUNDLE_MAX_BYTES` | `104857600`（100 MiB） | 世界模拟数据包上传的最大大小。 |
| `RC_PRESET_MAX_BYTES` | `5242880`（5 MiB） | SillyTavern 预设上传的最大大小。 |

## SMTP（邮件）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_SMTP_HOST` | `127.0.0.1` | SMTP 服务器主机名。留空则禁用邮件功能（账号激活令牌、密码重置令牌）。 |
| `RC_SMTP_PORT` | `1025` | SMTP 服务器端口。 |
| `RC_SMTP_USERNAME` | 空 | SMTP 认证用户名。 |
| `RC_SMTP_PASSWORD` | 空 | SMTP 认证密码。 |
| `RC_SMTP_USE_TLS` | `false` | 连接时使用 TLS（SMTPS / 端口 465 隐式 TLS）。 |
| `RC_SMTP_START_TLS` | `false` | 使用明文连接然后升级为 TLS（端口 587）。 |
| `RC_SMTP_SENDER` | `no-reply@localhost` | 所有外发邮件的 `From` 头部地址。 |

账号激活令牌和密码重置令牌通过邮件发送。未激活的账号在 `RC_PENDING_ACCOUNT_RETENTION` 秒后会被清理（默认 24 小时）。

## 公共 URL

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_PUBLIC_BASE_URL` | `http://127.0.0.1:5173` | 前端应用的对外 URL。用于构建邮件中的激活和密码重置链接。必须与用户实际访问的地址完全一致（包括协议）。 |

## 会话和认证

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_SESSION_SECRET` | *必填* | 用于签名会话 Cookie 的密钥。建议至少 32 字节。 |
| `RC_SESSION_COOKIE_NAME` | `roleplay_catalogue_session` | 会话 Cookie 的名称。 |
| `RC_SESSION_MAX_AGE` | `1209600`（14 天） | 会话最大存活时间（秒），每次请求时刷新。 |
| `RC_SESSION_COOKIE_SECURE` | `false` | 为会话 Cookie 设置 `Secure` 标志，仅在 HTTPS 下发送。生产环境应设为 `true`。 |
| `RC_ACTIVATION_TOKEN_MAX_AGE` | `86400`（24 小时） | 用户激活令牌的最大存活时间（秒）。 |
| `RC_PENDING_ACCOUNT_RETENTION` | `86400`（24 小时） | 清理未激活用户账号前的保留时间（秒）。 |
| `RC_ACCOUNT_CLEANUP_INTERVAL` | `21600`（6 小时） | 后台任务扫描过期待激活账号的间隔（秒）。 |
| `RC_PASSWORD_RESET_TOKEN_MAX_AGE` | `3600`（1 小时） | 密码重置令牌的最大存活时间（秒）。 |
| `RC_API_KEY_CLEANUP_INTERVAL` | `21600`（6 小时） | 后台任务清理过期 API 密钥的间隔（秒）。 |

应用支持两种认证模式：会话 Cookie（浏览器登录）和 Bearer API 密钥（程序化访问）。两者由路由器中的同一依赖层验证。

## 浏览器安全头

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RC_SECURITY_HEADERS_ENABLED` | `true` | 是否在 FastAPI 中间件层注入安全头。上游代理（Nginx、Cloudflare 等）管理时设为 `false`。 |
| `RC_CONTENT_SECURITY_POLICY` | 见 `example.env` | CSP 头值。默认包含严格的 `"default-src 'self'"` 策略及图片 data/blob 来源。前端加载外部资源或 API 时覆盖。 |
| `RC_HSTS_MAX_AGE` | `0` | HSTS `max-age`（秒）。零表示禁用。HTTPS 生产环境设为 `31536000`（一年）。 |
| `RC_HSTS_INCLUDE_SUBDOMAINS` | `false` | 在 HSTS 头中添加 `includeSubDomains` 指令。 |
| `RC_HSTS_PRELOAD` | `false` | 在 HSTS 头中添加 `preload` 指令。 |

> [!NOTE]
> Docker Compose 模式下，Nginx 边车直接提供前端响应。`NGINX_HSTS_HEADER` 和 `NGINX_CONTENT_SECURITY_POLICY` 对 Nginx 响应生效。建议同时设置 FastAPI 环境变量（用于 API 响应）和 Nginx 变量（用于 SPA）以保持一致策略。

## CSRF 保护

跨站请求伪造保护由一个中间件提供，该中间件要求每个不安全请求携带 `x-csrf-token` 头（GET 和 OPTIONS 请求除外）。令牌来自前一次请求中的 `SEC_COOKIE_NAME` Cookie。通过 Bearer Token 认证 API 请求可豁免 CSRF 检查。

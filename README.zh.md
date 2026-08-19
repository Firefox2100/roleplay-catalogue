# 角色扮演资源库

[![许可证：GPL v3](https://www.gnu.org/graphics/gplv3-88x31.png)](https://www.gnu.org/licenses/gpl-3.0.en.html)

一个开源的、可自托管的角色扮演资源目录系统。它为管理、分享 SillyTavern 角色卡、背景设定书、聊天预设、图片和世界模拟引擎世界提供私有平台——将控制权完全交给部署者，而非依赖商业平台。

## 用途

角色扮演资源库填补了私人或组织维护内容库的空白。它面向三类用户提供服务：

- **用户** — 发现、搜索和下载资源。
- **作者** — 创建、版本化并发布资源，支持协作编辑。
- **部署者** — 通过单一 Docker Compose 堆栈部署，无需外部依赖。

已部署的实例不进行内容过滤，也不自带内容；部署者控制所发布的内容。库中资源的许可证由各自作者决定（GPL-3.0 默认适用于平台本身，不适用于平台内托管的内容）。

## 功能特性

- **SillyTavern 角色卡** — 以 V3 格式上传和下载（V2 卡上传时自动转换）。
- **背景设定书** — 支持作为独立资源类型，可从角色卡链接，多个资源可复用同一本设定书。
- **聊天预设** — 创建、分享和下载 SillyTavern 生成预设。
- **世界模拟引擎** — 上传和提供 WorldSE 数据包。
- **图片管理** — 上传图片并为任何资源分配封面。
- **版本发布** — 支持草稿 → 发布流程，带编号版本历史和统一内容差异（含合并的背景设定书）。
- **衍生复刻** — 用户可 Fork 任何公共资源创建衍生版本，同时链接回原资源。
- **协作编辑** — 作者可邀请协作者编辑资源草稿（发布和删除仅作者可操作）。
- **搜索和过滤** — 按标签、分类、作者和评分发现资源，由 MongoDB Community Search 提供支持。
- **双认证模式** — Session Cookie 用于浏览器登录，Bearer API Key 用于程序化访问。
- **CSRF 保护** — 中间件强制不安全请求携带令牌头；API 密钥认证豁免。
- **国际化** — 内置英文和简体中文，由 `react-i18next` 提供。

## 快速开始

最快的运行方式是使用 Docker Compose。它将自动提供应用服务器、MongoDB 副本集（事务必需）、MinIO S3 存储后端和 MongoDB Community Search。

### 1. 克隆与配置

```sh
git clone https://github.com/Firefox2100/roleplay-catalogue.git
cd roleplay-catalogue
cp example.env .env
```

编辑 `.env`，至少设置以下项：

```sh
# 你自己的密钥（32 字符以上）
RC_SESSION_SECRET=change-me-to-something-secret

# MongoDB Community Search 密码
MONGOT_PASSWORD=change-me-too-S3cr3t-Pass

# 用户访问的 URL
RC_PUBLIC_BASE_URL=http://localhost:8080
```

完整可配置选项列表请参阅 [配置选项](docs/zh/configuration.md)。

### 2. 启动堆栈

```sh
docker compose up -d
```

等待约一分钟用于 MongoDB 初始化和存储桶创建。随后在浏览器中打开 `http://localhost:8080`。

### 3. 注册

访问首页，点击**注册**，填写邮箱和密码，到邮箱中点击激活链接即可。从首页或你的个人资料页创建你的第一个资源。

### 4. 停止和重启

```sh
docker compose down          # 停止容器（数据卷保留）
docker compose down -v       # 停止并删除全部
docker compose restart       # 重启所有服务
docker compose logs -f       # 实时查看日志
```

## 仓库结构

```
├── src/roleplay_catalogue        # FastAPI 后端（Python）
│   ├── routers/                  # API 端点定义
│   ├── services/                 # 业务逻辑、数据库/仓库层
│   ├── models/                   # Pydantic 模型和 MongoDB 架构
│   ├── components/               # 认证组件、账号服务
│   └── misc/                     # 配置、错误类型、辅助工具
├── frontend/                     # React SPA（Vite + React 19）
│   ├── src/                      # 页面、API 客户端、认证上下文
│   └── package.json
├── docs/                         # 静态站点源文件（通过 zensical 构建 MkDocs）
│   ├── en/                       # 英文文档
│   └── zh/                       # 中文翻译
├── deploy/                       # Docker 文件（Dockerfile、Nginx、Supervisor、初始化脚本）
├── compose.yaml                  # Docker Compose 定义
├── example.env                   # 所有可配置变量
└── pyproject.toml                # Python 项目元数据和依赖
```

## 许可证

角色扮演资源库遵循 [GPL v3 许可证](https://www.gnu.org/licenses/gpl-3.0.en.html) 的免费软件。所有衍生作品也必须使用 GPL v3。本软件不提供任何保修。使用即表示你同意这些条款以及[免责声明](docs/zh/index.md)。

## 链接

- **GitHub：** [Firefox2100/roleplay-catalogue](https://github.com/Firefox2100/roleplay-catalogue)
- **文档：** [https://firefox2100.github.io/roleplay-catalogue/](https://firefox2100.github.io/roleplay-catalogue/)

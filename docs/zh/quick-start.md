# 快速开始

启动角色扮演资源库最简单的方式是使用 `docker compose`。它会同时启动应用、单节点 MongoDB 副本集、MongoDB Community Search、Redis 和 MinIO 对象存储。

## 前提条件

- [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/) v2.20+

## 步骤

1. **复制示例环境文件**

   ```sh
   cp example.env .env
   ```

2. **编辑 `.env`，至少设置以下变量**

   | 变量 | 示例值 | 说明 |
   |---|---|---|
   | `RC_SESSION_SECRET` | `a3f1b7c9d2e4f6...` | 至少 32 字节 |
   | `MONGOT_PASSWORD` | `change-this-search-password` | MongoDB Community Search 使用的随机密码 |
   | `RC_PUBLIC_BASE_URL` | `http://localhost:8080` | 用户访问的前端 URL |

   完整选项请参阅 [配置选项](configuration.md)。其余变量会使用合理的默认值。

3. **启动容器服务**

   ```sh
   docker compose up -d
   ```

   首次运行时，Docker 会拉取镜像、启动各项服务，并完成 MongoDB 与对象存储的初始化。这可能需要一至两分钟。

4. **打开资源库**

   打开 `http://localhost:8080`（或你通过 `CATALOGUE_PORT` 配置的端口）。首次访问首页你会看到"注册"按钮——注册账号后即可登录。

## 停止和重启

```sh
docker compose down          # 停止并移除容器（保留数据卷）
docker compose down -v       # 停止并移除一切，包括数据卷
docker compose restart       # 重启所有正在运行的服务
```

## 查看日志

```sh
docker compose logs -f catalogue   # 仅查看应用服务器日志
docker compose logs -f             # 查看所有服务日志
```

## 一键默认启动

如果你想直接启动而不修改 `.env`，仅设置这三项默认值即可：

```sh
cat > .env <<EOF
RC_SESSION_SECRET=change-me-to-something-secret
MONGOT_PASSWORD=change-me-too-S3cr3t-Pass
RC_PUBLIC_BASE_URL=http://localhost:8080
EOF

docker compose up -d
```

> [!TIP]
> MongoDB 副本集是事务的必要条件。单节点副本集足以用于开发环境；生产环境建议使用多节点副本集以获得高可用性。

> [!NOTE]
> 端口说明：应用容器监听 `8080`，并映射到 `CATALOGUE_PORT`（默认也是 `8080`）。使用 Compose 时，MinIO 管理控制台位于 `9001` 端口。Redis 和 MongoDB 默认不对宿主机开放端口。

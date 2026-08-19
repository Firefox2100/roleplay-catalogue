# 快速开始

启动角色扮演资源库最快的方式是使用 `docker compose`。这条命令会启动应用服务器、单节点 MongoDB 副本集（支持事务）、MongoDB 社区搜索（用于未来全文和向量搜索）以及 MinIO S3 兼容存储后端——一个命令即可运行全套环境。

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
   | `MONGOT_PASSWORD` | `my-redis-12345` | 随机密码，用于 MongoDB Community Search |
   | `RC_PUBLIC_BASE_URL` | `http://localhost:8080` | 用户访问的前端 URL |

   完整选项请参阅 [配置选项](configuration.md)。其余变量会使用合理的默认值。

3. **启动容器堆栈**

   ```sh
   docker compose up -d
   ```

   首次运行时，Docker 会拉取镜像、启动容器，并执行两个一次性初始化任务：创建 S3 存储桶、将 MongoDB 配置为副本集。这可能需要一至两分钟。

4. **打开资源库**

   导航至 `http://localhost:8080`（或你通过 `CATALOGUE_PORT` 配置的端口）。首次访问首页你会看到"注册"按钮——注册账号后即可登录。

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
> 端口说明：容器内 catalogue 监听 `8080`，映射到 `CATALOGUE_PORT`（默认 `8080`）。运行 compose 堆栈时，MinIO Console 可在端口 `9001` 访问。

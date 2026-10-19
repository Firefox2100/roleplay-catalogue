# 搜索与过滤

角色扮演资源库可搜索资源名称和描述，也支持按资源类型、标签、作者和发布状态过滤。结果可按最近更新或热度排序；文本搜索优先按相关度排序。

## 概览

搜索与过滤通过单一的**资源列表**端点协作工作。你可以组合任意多的过滤条件 — 系统返回所有指定条件均匹配的结果。

### 搜索索引

`searchString` 参数使用 MongoDB `$text` 查询和加权文本索引。名称的权重高于描述。标签以及上传的角色卡、世界书、预设和世界内容不在该文本索引中。

## 过滤选项

### 按资源类型

过滤到单一资源分类：

```
GET /resources?resourceType=sillytavern/character
```

| 接受的值 | 描述 |
|---|---|
| `sillytavern/character` | SillyTavern 角色卡 |
| `sillytavern/lorebook` | 世界书资源 |
| `sillytavern/preset` | 聊天完成预设 |
| `world-simulation-engine/world` | World Simulation Engine 世界 |
| `dsh-agentic-roleplay/world` | DeepSeek Harness Agentic Roleplay 世界 |
| `core/image` | 独立图片资源 |

### 按标签

使用 `tags` 参数按一个或多个标签过滤。提供多个标签时，采用**AND 逻辑**组合 — 资源必须具有*所有*指定标签才能匹配。

```
GET /resources?tags=cyberpunk&tags=magic
```

**标签自动完成**请使用专用的标签端点：

```
GET /resources/tags?search=cy&limit=10
```

此端点返回最多 25 个匹配的标签名称。标签匹配不区分大小写，并按使用频率排序（最多使用的前置）。

### 按作者

按特定作者的用户名过滤资源：

```
GET /resources?author=Alice
```

作者过滤器会查找所提供的用户名。如果作者不存在，则返回空结果集。

### 按发布状态

仅限制返回至少有一个已发布版本的资源：

```
GET /resources?publishedOnly=true
```

默认情况下，列表端点包含所有资源而不考虑发布状态 — 草稿和已发布资源均会显示。

### 按全文搜索

提供关键字字符串：

```
GET /resources?searchString=dragon
```

搜索由 MongoDB 进行分词（词级匹配）。结果按**相关度评分**（降序）排列，之后以 `updatedAt`（降序）作为次级排序依据。

## 可见性与访问

搜索结果遵循资源的可见性设置：

| 草稿可见性 | 谁在结果中可见 |
|---|---|
| `PUBLIC`（公开） | 所有用户 |
| `AUTHENTICATED`（已登录用户可见） | 已登录用户 |
| `PRIVATE`（私有） | 作者、协作者及已被授予访问权限的用户 |

私有资源版本进一步过滤：仅有 `PUBLIC` 或 `AUTHENTICATED` 可见性的版本出现在搜索结果中（搜索者为作者除外）。

## 分页

结果使用 offset 和 limit 进行分页：

```
GET /resources?offset=0&limit=50
```

| 参数 | 默认值 | 范围 |
|---|---|---|
| `offset` | `0` | ≥ 0 |
| `limit` | `50` | 1–100 |

响应中包含 `nextOffset` 字段：如果 `nextOffset` 存在，说明还有更多结果，你可以将 `offset` 设为该值来获取更多结果。如果 `nextOffset` 为 `null`，说明已到达结果末尾。

响应格式：

```json
{
  "items": [...],
  "nextOffset": 50
}
```

## 排序

资源排序规则如下：

- **搜索结果**（提供 `searchString`）：相关度评分（降序），然后 `updatedAt`（降序）。
- **非搜索结果**：默认按 `updatedAt` 降序。
- **热门结果**（`sort=popular`）：依次按下载次数、浏览次数和 `updatedAt` 降序。计数归属于资源本身，各个发布版本共用同一组总数。

## 浏览与下载次数

资源卡片和详情页会显示匿名使用次数：

- 应用请求某项资源以生成详情页时，记录一次**浏览**。
- 通过后端下载发布文件，或生成签名下载链接时，记录一次**下载**。

这些数字表示请求次数，并不代表独立访客人数。同一人重复打开或下载会重复计数，系统不会为此记录访客身份。统计数据保存在 Redis 中，管理员备份数据时应将 Redis 一并纳入。

## 提示与注意事项

> [!TIP]
> **使用标签过滤 + publishedOnly 进行发现。** 窄标签配合 `publishedOnly=true` 是寻找优质社区内容而不过滤进行中的草稿的理想组合。

> [!NOTE]
> **自动完成端点感知可见性。** 已登录用户看到的标签涵盖 `AUTHENTICATED` 资源以及 `PUBLIC` 资源。未登录用户仅看到 `PUBLIC` 资源标签。

> [!NOTE]
> **导入时标签去重。** 导入卡片或世界书时，新标签仅在资源现有标签列表不存在时才被追加。

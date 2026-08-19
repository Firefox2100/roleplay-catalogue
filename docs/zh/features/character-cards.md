# character-cards.md

## 概述

Roleplay Catalogue 使用 SillyTavern 角色卡格式作为核心内容类型。无论是从头创建新角色，还是上传已有角色卡，Catalogue 都与 SillyTavern 广泛使用的 V2 和 V3 格式保持兼容。Catalogue 中的角色卡用于存储草稿数据、维护完整的版本历史，并可关联最多 50 本来自 Catalogue 的 Lorebook（背景设定书）。

## 使用方法

### 创建或上传角色卡

以 **JSON 文件**（V2 或 V3）或嵌入 SillyTavern 卡牌数据的 **PNG 文件**形式上传角色卡。Catalogue 会自动检测并解析你上传的格式。

发布时，Catalogue 会生成一个完整的、自包含的角色卡：所有关联的 Lorebook 会直接合并到输出 JSON 中，该文件无需任何依赖即可直接用于 SillyTavern。

### 导入已有角色卡

如果你向已有草稿数据的角色卡导入数据，系统会将导入数据与已有草稿进行**合并**：

- **数组**（如 `messages`、`post_history` 或 `creator_notes`）将被连接。
- **对象/字典**将按键逐个合并。
- 导入数据中缺失的字段会从现有草稿中填充。
- 草稿中存在但导入数据中不存在的字段保持不变。

### 从 PNG 提取

如果上传的是 PNG 格式角色卡，Catalogue 会从 `tEXt` 块中读取嵌入的 JSON，并同时**自动设置角色卡的封面图**。

### Fork 已发布版本

你可以 Fork 角色卡的任意已发布版本。Fork 会创建一个衍生角色卡，其显示名称以 **"Forked from …"** 开头。新资源的 `character_version` 字段将继承自你 Fork 的那张角色卡的版本标签。

### 草稿数据

你可以在编辑器页面通过 **导出草稿（Export Draft）** 操作独立导出草稿数据。导出内容包括：

- **`.draft.json`** — 原始 SillyTavern 角色卡数据。
- **`.draft.png`** — 在 `tEXt` 块中嵌入草稿卡数据的 PNG 文件，可直接用于 SillyTavern。

### 发布元数据

发布角色卡时，以下元数据会被追加到 SillyTavern 卡牌输出中：

- **标签**（来自 Catalogue 资源条目）
- **描述**（来自 Catalogue 资源条目）

发布者默认使用你的显示名称作为创作者名。

### 关联 Lorebook

一张角色卡最多可以关联 **50 本 Lorebook**。关联方式包括：

- **Lorebook 的草稿**（实时 — 下一次发布前，卡牌会跟随 Lorebook 的所有编辑更改）。
- **已发布的固定版本**（锁定 — 关联时的状态即固定不变）。

## 限制

| 限制项 | 上限 |
|--------|------|
| 最大上传大小 | 20 MiB（20 × 1024 × 1024 字节） |
| 关联 Lorebook | 每个角色卡最多 50 本 |
| 支持的格式 | JSON（V2 / V3）、PNG（嵌入 JSON） |
| Fork 名称前缀 | "Forked from" |

## 提示与注意事项

- **PNG 导入速度更快。** 上传 SillyTavern PNG 可以跳过 JSON 步骤，并免费获得封面图。
- **合并的 Lorebook = 可携带卡牌。** 发布时，关联的 Lorebook 会被编译到输出 JSON 中。这意味着无论关联的 Lorebook 是否仍在 Catalogue 中存在，你的角色卡始终包含完整的定义。
- **覆盖时注意合并行为。** 由于合并是增量式的（数组内容会连接），多次导入相同的 JSON 会导致重复条目。导入相同内容前请使用"替换"或先清空草稿。
- **版本追踪。** `character_version` 字段不仅是装饰性文字 — 它包含在序列化卡牌数据中，你可以在对戏或 Lore 中引用它。

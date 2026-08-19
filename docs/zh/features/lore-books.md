# lore-books.md

## 概述

SillyTavern Lorebook 是 Catalogue 的一等资源。你可以独立上传、编辑、版本化、Fork 和发布 Lorebook，也可以将其关联到角色卡上，使 Lorebook 数据随角色卡一起在发布时捆绑交付。

## 使用方法

### 创建 Lorebook

Lorebook 由一组**条目（entries）**构成，用于为角色提供游戏内上下文信息。每本 Catalogue Lorebook 最多可容纳 50 个条目。你可以通过上传表单创建 Lorebook 草稿内容，也可以从现有的 SillyTavern Lorebook 导入。

系统会自动检测上传的 JSON 文件使用的是当前 **`lorebook_v3`** 规范还是旧版 **V2** 格式，并分别进行解析。

### 导入 Lorebook

你可以从以下三种来源导入 Lorebook 数据：

- **独立 JSON 文件** — 完整的 SillyTavern V2 或 V3 Lorebook 文件。
- **嵌入角色卡 JSON 中** — 导入包含 Lorebook 区块的角色卡时，Catalogue 会同时解析角色卡和其中的 Lorebook。
- **嵌入 PNG 角色卡中** — Catalogue 会从 tEXt 块中与卡牌一并读取 Lorebook 数据。

### 合并行为

如果你向已有草稿条目的 Lorebook 资源导入数据，将使用与角色卡相同的合并策略：

- 保留现有条目，新条目追加到末尾。
- 类似字典的字段按键逐个合并。
- 导入数据中缺失的值会从现有草稿中填充。

如需完全替换所有内容，请先清空草稿。

### 从角色卡关联

每张角色卡的草稿都维护着一个**已关联 Lorebook 引用**的列表。对于每个关联项，你可以选择以下两种模式之一：

| 模式 | 行为 |
|------|------|
| **关联草稿（Link Draft）** | 实时 — 当角色卡重新发布时，将始终使用最新发布的 Lorebook 内容。 |
| **关联已发布版本（Link Release Version）** | 锁定 — 角色卡保留关联时刻 Lorebook 的精确状态。 |

角色卡发布时，所有关联的 Lorebook 都会**合并到编译后的 JSON 中**。发布用户无需单独导出或下载 Lorebook。

### 封面图

Lorebook 可以设置封面图。通过编辑器的**封面图选择器**进行设置。封面图需满足标准图片上传要求（详见 [图片](images.md) 文档）。

### Fork

你可以对已发布的 Lorebook 进行 Fork。Fork 后的 Lorebook 会携带源版本的所有已关联 Lorebook 引用，便于构建 lore 扩展链。

## 限制

| 限制项 | 上限 |
|--------|------|
| 每个 Lorebook 最大条目数 | 50 |
| 每张角色卡最多关联 Lorebook | 50 |
| 支持的 Lorebook 规范 | `lorebook_v3`（当前）、V2（旧版，自动检测） |
| 封面图最大大小 | 20 MiB |

## 提示与注意事项

- **关联是一把双刃剑。** 当已发布的源 Lorebook 发生变更时，所有链接了*实时草稿*的角色卡在下次发布时都会反映该更改。如需稳定性，请链接已锁定的发布版本。
- **删除保护。** 当前被角色卡链接的 Lorebook 无法从 Catalogue 中删除。必须先从角色卡上移除关联才能删除。
- **PNG 导入很方便。** 如果你的 Lorebook 嵌入在 PNG 角色卡中，一次上传即可获得两者 —非常适合分享完整的卡牌集合。
- **版本化是自动的。** 每次发布时，都会创建一个新的不可变版本并添加到版本历史中 — 你可以随时回滚或进行差异对比。

# Search & Filtering

Roleplay Catalogue searches resource names and descriptions. You can also filter by resource type, tags, author, and publication status. Results are paginated and can be ordered by recency or popularity; text searches use relevance first.

## Overview

Search and filtering work together via a single **list resources** endpoint. You can combine as many filters as you like — the system returns results matching all specified criteria.

### Search index

The `searchString` parameter uses MongoDB's `$text` query against a weighted text index. Resource names carry more weight than descriptions. Tags and the contents of uploaded cards, lorebooks, presets, and worlds are not part of this text index.

## Filtering options

### By resource type

Filter to a single resource category:

```
GET /resources?resourceType=sillytavern/character
```

| Accepted values | Description |
|---|---|
| `sillytavern/character` | SillyTavern character cards |
| `sillytavern/lorebook` | Lorebook resources |
| `sillytavern/preset` | Chat completion presets |
| `world-simulation-engine/world` | World Simulation Engine worlds |
| `dsh-agentic-roleplay/world` | DeepSeek Harness agentic-roleplay worlds |
| `core/image` | Standalone image resources |

### By tags

Filter by one or more tags using the `tags` parameter. When multiple tags are provided, they are **combined with AND logic** — a resource must have *all* specified tags to match.

```
GET /resources?tags=cyberpunk&tags=magic
```

For **tag autocomplete**, use the dedicated tags endpoint:

```
GET /resources/tags?search=cy&limit=10
```

This returns up to 25 matching tag names. Tags are matched case-insensitively and sorted by usage count (most used first).

### By author

Filter to resources by a specific author's username:

```
GET /resources?author=Alice
```

The author filter resolves the supplied username. If the author does not exist, an empty result set is returned.

### By publication status

Limit results to resources that have at least one published version:

```
GET /resources?publishedOnly=true
```

By default, the list endpoint includes visible drafts and published resources. Visibility rules still apply.

### By full-text search

Provide a keyword string:

```
GET /resources?searchString=dragon
```

The search is tokenised by MongoDB (word-level matching). Results are sorted by **relevance score** (descending) followed by `updatedAt` (descending) as a tiebreaker.

## Visibility and access

Search results respect resource visibility:

| Draft visibility | Who sees it in results |
|---|---|
| `PUBLIC` | All users |
| `AUTHENTICATED` | Logged-in users |
| `PRIVATE` | Author, co-authors, and users explicitly granted access |

Private resource versions are further filtered: only versions with `PUBLIC` or `AUTHENTICATED` visibility appear in search results (unless the searcher is the author).

## Pagination

Results are paginated using offset and limit:

```
GET /resources?offset=0&limit=50
```

| Parameter | Default | Range |
|---|---|---|
| `offset` | `0` | ≥ 0 |
| `limit` | `50` | 1–100 |

The response includes a `nextOffset` field: if `nextOffset` is present, additional results exist and you can fetch them by setting `offset` to that value. If `nextOffset` is `null`, you have reached the end of results.

Response format:

```json
{
  "items": [...],
  "nextOffset": 50
}
```

## Sorting

Resources are sorted by:

- **Search results** (`searchString` provided): relevance score (descending) then `updatedAt` (descending).
- **Non-search results**: `updatedAt` descending by default.
- **Popular results** (`sort=popular`): download count, then view count, then `updatedAt`, all descending. Engagement belongs to the canonical resource, so every release contributes to the same totals.

## View and download counts

Resource cards and detail pages show anonymous engagement counts:

- A **view** is recorded when the application requests a resource to build its detail page.
- A **download** is recorded when a release is downloaded through the backend or when a signed download link is created.

These are request counts, not unique visitor counts. Repeated requests are counted separately and the catalogue does not attach visitor identities to them. The counters are stored in Redis, which administrators should include in their persistence and backup plans.

## Tips and notes

> [!TIP]
> **Use tag filtering + publishedOnly for discovery.** The combination of narrow tags with `publishedOnly=true` is ideal for finding polished community content without seeing in-progress drafts.

> [!NOTE]
> **The autocomplete endpoint is visibility-aware.** Logged-in users see tags used on `AUTHENTICATED` resources in addition to `PUBLIC` ones. Unauthenticated users only see `PUBLIC` resource tags.

> [!NOTE]
> **Tags are deduplicated on import.** When you import a card or lorebook, new tags are appended only if they are not already present in the resource's tag list.

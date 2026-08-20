# Search & Filtering

The Roleplay Catalogue provides full-text search across characters, lorebooks, presets, and worlds, along with filtering by resource type, tags, author, and publication status. Results are paginated and sortable by relevance or date.

## Overview

Search and filtering work together via a single **list resources** endpoint. You can combine as many filters as you like — the system returns results matching all specified criteria.

### Search index

The `searchString` parameter uses **MongoDB Community Search** (`$text` queries) against a text index on the resources collection. The index includes:

- Resource metadata (name, description, tags)
- Rendered content from the draft's type-specific data (e.g. the character card's full JSON, the lorebook entries, the preset parameters)
- For character cards, the **merged content** — the card data combined with the text of any linked and merged lorebook entries

This means searching a character card can match keywords found either in the card itself or in attached lorebooks.

## Filtering options

### By resource type

Filter to a single resource category:

```
GET /resources?resourceType=character
```

| Accepted values | Description |
|---|---|
| `character` | SillyTavern character cards |
| `lorebook` | Lorebook resources |
| `preset` | Chat completion presets |
| `world` | World Simulation Engine worlds |
| `image` | Standalone image resources |

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

The author filter uses the exact username (case-sensitive). If the author does not exist, an empty result set is returned.

### By publication status

Limit results to resources that have at least one published version:

```
GET /resources?publishedOnly=true
```

By default, the list endpoint includes resources regardless of publication status — drafts and published resources alike appear.

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
- **Non-search results**: `updatedAt` (descending — newest updates first).

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
> **Search merges lorebook content for characters.** If a character card links a lorebook, searching for keywords in that lorebook will match the character even if the keyword does not appear on the card itself.

> [!NOTE]
> **Tags are deduplicated on import.** When you import a card or lorebook, new tags are appended only if they are not already present in the resource's tag list.

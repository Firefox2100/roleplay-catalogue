# Collaborative Editing (Co-authors)

Co-authoring lets a resource's **author** invite other registered users to edit the draft. Co-authors share full draft-editing rights — uploading data, changing metadata, linking lorebooks, and exporting — while only the author retains publish and delete permissions.

## Overview

This feature is designed for:

- **Multi-writer groups** working on a shared resource (e.g. a character expanded by several community members).
- **Hires and alternates** where a collaborator adds content (dialogue, trivia, expansions) that the author reviews and accepts.
- **Lorebook teams** where multiple writers contribute entries to a shared universe.

### Who can do what

| Action | Author | Co-author | Other user |
|---|---|---|---|
| View draft | Yes | Yes | Depends on visibility |
| Edit draft data | Yes | Yes | No |
| Edit metadata (name, description, tags) | Yes | Yes | No |
| Upload / change cover image | Yes | Yes | No |
| Link / unlink lorebooks | Yes | Yes | No |
| Export draft | Yes | Yes | No |
| Publish a release | Yes | No | — |
| Delete the resource | Yes | No | — |
| Manage co-author list | Yes | No | — |
| Change version visibility after publish | Yes | No | — |

## How to add a co-author

1. Navigate to the resource's **Co-authors** section on the detail or edit page.
2. Enter the **exact username** of the user you want to invite.
3. Click **Add Co-Author**.
4. The invitation is live — the user gains full draft access immediately.

## How to remove a co-author

The author can remove any co-author from the same **Co-authors** section.

### By the co-author

A co-author can leave a resource themselves. Their earlier edits remain part of the draft and release history.

### On account deletion

When a user deletes their account, they are automatically removed from every resource's co-author list. The author of that resource retains full control.

## Contribution visibility on forks

When a co-author forks a resource they contributed to:

- Their draft edits are included in the fork's data.
- The version published by the fork inherits the merged data snapshot.
- The `contentDiff` on the published version shows the unified diff including all changes from every contributor.
- On the resource detail page, co-authors are listed alongside the author username.

## Constraints

| Constraint | Limit |
|---|---|
| Username format | Exact match, case-sensitive |
| Author themselves | Cannot be added as a co-author (no duplicates) |
| Duplicate invites | A user who is already a co-author cannot be added again |
| Deleting a lorebook linked on a co-authored resource | Only the lorebook's author can delete it; a non-author co-author of a character cannot delete the lorebook |
| Co-author count | No configured limit |

## Tips and notes

> [!TIP]
> **Pick your co-authors carefully.** Anyone with a co-author link can edit and export the draft. If you have sensitive content, consider changing the draft's visibility before inviting external collaborators.

> [!NOTE]
> **Visibility independence.** The draft visibility controls who can *view* the resource. The co-author list controls who can *edit* the draft. A public resource with a private co-author still grants that co-author edit access.

> [!NOTE]
> **Co-authors share draft access.** Authors and co-authors can upload data, update metadata, and export drafts. Publishing, deletion, and co-author management remain author-only.

> [!IMPORTANT]
> **Tag order is preserved across contributors.** When multiple co-authors append tags, the final tag list reflects the order of addition. Duplicate tags are automatically suppressed by the import merge logic.

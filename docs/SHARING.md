# Sharing the project

## Short announcement

> I built a local-first plant tracker that your coding agent can update from photos. Send one plant or a whole batch, and the included skill organizes the inventory, keeps care history, updates priorities, and tells you what needs attention. It works with both Codex and Claude Code, and it is a static HTML file with no database or account, so you can clone it and keep your data in your own repository.

Add your repository URL after the paragraph.

## Longer announcement

> Plant care notes tend to end up scattered across spreadsheets, photo albums, and reminders, so I built a small photo-based tracker around a single static HTML page. The repository includes an agent skill — it runs on both Codex and Claude Code from the same files — that can start a new collection, bulk-import many plant photos, group multiple views of the same plant, maintain a care reference, and update treatment or repotting history over time. It validates priorities and image links automatically, works locally in VS Code, and can be published with GitHub Pages. Photos are gitignored by default, so your collection stays on your machine unless you deliberately publish it. Clone it and send your agent some plants.

## Suggested repository details

**Description**

```text
Local-first photo plant tracker with a Codex and Claude Code skill for bulk imports and care updates.
```

**Topics**

```text
plants houseplants plant-care codex codex-skill claude claude-code claude-skill agent-skills local-first static-html personal-dashboard
```

## Privacy note

The tracker ships empty and `images/` is gitignored, so sharing the repository shares the
tool, not your plants. Review [Privacy](PRIVACY.md) before deliberately publishing any photo.

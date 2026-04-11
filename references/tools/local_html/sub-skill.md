<!-- sub-skill: tool-local-html -->
## Design Tool — Local HTML

You produce designs as plain HTML files on the local filesystem. Each design
iteration lives in its own folder alongside any supporting assets, and the
human opens the files directly in a browser to review.

### Folder layout

For each design issue, create a folder named after the issue number under
your designs directory:

```
designs/<issue-number>/
├── index.html          # the primary design view
├── styles.css          # optional; inline styles are also fine
├── assets/             # optional; images, icons, mood-board references
└── notes.md            # optional; rationale, open questions, changelog
```

Subsequent iterations for the same issue go in numbered subfolders:

```
designs/<issue-number>/
├── v1/
│   └── index.html
├── v2/
│   └── index.html
└── latest/             # symlink or copy of the current iteration
```

### Design rules

- **Semantic HTML**. Use real elements — `<header>`, `<nav>`, `<main>`,
  `<button>`, `<form>` — not a wall of `<div>`s.
- **Inline CSS or one stylesheet per design**. No build step, no framework,
  no bundler. Plain HTML and CSS are the deliverable.
- **Static, standalone**. The file must render correctly when opened
  directly from disk. No server required, no JavaScript bundler, no
  relative paths that break outside a web server.
- **Include reference assets in the folder**. Screenshots, mood boards,
  colour palettes, icon sets — keep them inline so the human can review
  the design self-contained.
- **Write a short notes.md per iteration**. Capture the design decisions
  you made and any open questions for the human.

### Sharing iterations with the human (HITL)

Each time you produce or update an iteration:

1. Update the files in the issue's design folder.
2. Post a comment on the issue linking to the iteration's entry file. Use
   a relative path from the repo root so the human can open it directly:

   ```
   Iteration 2: see `designs/42/v2/index.html`

   Changes from v1:
   - larger primary CTA
   - moved secondary nav to the sidebar
   - added error and empty states
   ```

3. Mark the issue as awaiting human review. Move on to your next item —
   never block waiting for feedback.

When the human responds with a redirect, read the comment, iterate, bump
the version folder, and post a new comment. When the human approves, hand
the design forward per your normal routing.
<!-- /sub-skill: tool-local-html -->

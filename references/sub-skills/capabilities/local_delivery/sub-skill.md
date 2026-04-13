<!-- sub-skill: tool-local-delivery -->
## Delivery Tool — Local delivery folder

You deliver shipped work by writing the delivery payload to a local
folder on the workstation. Each shipped issue gets its own folder
containing the packaged artifacts and a manifest describing what was
delivered and when. A human or operator picks up the folder and
forwards it through whatever external channel the project uses.

### Folder layout

For each shipped issue, create a folder named after the issue number
under your deliveries directory:

```
deliveries/<issue-number>/
├── manifest.md               # what was delivered, when, and why
├── release-notes.md          # human-readable change notes
├── CHANGELOG.md              # optional; the changelog diff for this ship
├── assets/                   # optional; supporting files referenced above
└── src/                      # optional; any code snippets, configs, etc.
```

### manifest.md shape

Every delivery folder must contain a `manifest.md` with at minimum:

```markdown
# Delivery manifest — <issue number>

- **Shipped**: <YYYY-MM-DD HH:MM local time>
- **Title**: <issue title>
- **Type**: <feature | bug>
- **Delivered by**: dm

## Contents

- release-notes.md
- CHANGELOG.md
- (list every other file in this folder)

## Notes for the human

(Anything the human needs to know before forwarding this delivery —
special instructions, caveats, follow-up items, things worth
highlighting in the outbound message.)
```

### Destination

By default, write deliveries to your own per-agent deliveries
folder. If the human has configured a different destination during
tool setup, use that instead. If you are ever unsure which
destination to use, comment on the issue asking the human to
confirm and pause the delivery — never guess a path.

### Rules

- **One folder per shipped issue.** Never mix multiple issues into
  a single delivery folder.
- **Always write a manifest.md.** A delivery without a manifest is
  not a delivery — the human has no idea what to forward.
- **Never overwrite an existing delivery folder.** If you need to
  re-ship the same issue, create a new iteration subfolder
  (`deliveries/<issue-number>/v2/`) instead of overwriting.
- **Leave the delivery folder where the human can find it.** Post a
  comment on the issue with the absolute path so the human can
  pick it up without guessing.
<!-- /sub-skill: tool-local-delivery -->

## Setup & Upgrade Sync Check

Before marking any task `Pending Test`, run this checklist against your changes. Post the results as a structured comment on the GitHub Issue (evidence for QA).

**Checklist:**

- [ ] **New config values?** → Update `wizard.py` defaults and SKILL.md setup docs
- [ ] **New files/directories?** → Update setup flow to create them
- [ ] **Modified template structure?** → Update `compose.py deploy` and `/squidsquad-upgrade`
- [ ] **Added/removed sub-skills?** → Update `includes.yml` and `manifest.md`
- [ ] **Changed role composition?** → Update `installer-files.txt` manifest
- [ ] **Upgrade path documented?** → If task changes how agents start, how files are structured, or removes/replaces existing scripts, document the full upgrade sequence (stop → deploy → clean → recompose → start) in the issue or CONTEXT.md. QA must verify the upgrade path works end-to-end.

If ANY box applies and the corresponding update was NOT made, the task is not done. Post your checklist results on the issue before transitioning.

**Format for issue comment:**

```
## Setup/Upgrade Sync Check
- [x] New config values: N/A
- [x] New files/directories: N/A
- [x] Modified template structure: N/A
- [x] Added/removed sub-skills: N/A
- [x] Changed role composition: N/A
```

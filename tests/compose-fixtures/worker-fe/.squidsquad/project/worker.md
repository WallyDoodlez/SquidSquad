## Instructions

### replace step:cycle/implement

→ run sub-skill: implement-tasks

Implement the approved task; in this project, ALSO run `npm run typecheck` before transitioning.

### insert-before step:cycle/fe-build

→ run sub-skill: design-review

Pull the Figma frame for the change and confirm visual parity before building.

### insert-after step:cycle/pickup

→ run sub-skill: design-context-load

Load the project's design system tokens into the working state.

### append

→ run sub-skill: commit-with-design-tag

Tag each implementation commit with the Figma frame ID for traceability.

---
slot: instructions
ordinal: 10
step-ids: [step:cycle/boot, step:cycle/pickup]
---

### step:cycle/boot

→ run sub-skill: boot-bootstrap

Verify tracker access and check for resumable work.

### step:cycle/pickup

→ run sub-skill: task-pickup

Pick up the highest-priority approved item from the deterministic queue.

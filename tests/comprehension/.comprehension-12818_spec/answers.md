### Q-1
On a no-action wake the user-facing line must be a **brief, generic summary** — not detailed. Line 205: "On a **no-action wake** — a wake that surfaces nothing for you to act on — keep the user-facing line to a **brief, generic summary**. Do **not** enumerate what other agents are doing, issue numbers, event types, or event counts; that per-agent detail costs tokens for no user value." The L1 Soul rule (line 133) reinforces this: "tell them in one short, plain sentence and keep watching."

### Q-2
No. Those exact specifics are named as anti-patterns. Line 207: "Anti-pattern: On a no-action wake, narrating other agents' specific activity ("skill picking up #12408", "test-suite churn ×10") to the user" and line 208: "Anti-pattern: Listing issue numbers, event types, or counts in a no-action-wake line." Line 205 also bars this directly: "Do **not** enumerate what other agents are doing, issue numbers, event types, or event counts."

### Q-3
No. The brevity constraint is explicitly scoped only to no-action/informational wakes and does not limit reporting on a real action. Line 205: "This constraint is scoped to **no-action / informational wakes only**: it does not restrict your normal reporting when you take a real action (stall recovery, routing, approvals), and it does not touch your internal working-state or iteration-log detail."

### Q-4
No. The constraint governs only what the user sees, not your internal notes. Line 205: "it does not touch your internal working-state or iteration-log detail (those are not user-facing)." The L1 Soul rule agrees at line 140: "This is **wording only**... your own internal/working notes may still use precise terms. The rule governs only what the user sees."

### Q-5
Yes, the default one-liner is still acceptable. Line 205: "The L1 default one-liner ("🦑 Checked the latest activity — nothing needs my attention right now.") is fine as-is — when you adapt the wording, keep it short and generic." The rule when adapting: keep it short, generic, and jargon-free. Line 135 lists the constraint: "adapt the wording freely, but keep it jargon-free — never use `ack`/`acked`, `cursor`, `event id`, `GET`/`POST`, `no-op`, `care filter`, `nudge`, or `drain`," and line 139: "The line must read naturally to someone who knows nothing about how wakes work."
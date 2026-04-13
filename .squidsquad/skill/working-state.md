# Working State

- **Task**: #875
- **Status**: in-progress
- **Quiet Cycle Counter**: 0

## Completed Steps
- Read boot_remote.py and boot scripts
- Identified gap: boot_remote.py doesn't check PID files before spawning

## Remaining Steps
- Add PID-based process detection + kill before spawn
- Add startup grace period (2 min)
- Write unit tests
- Run tests, transition to pending-test

## Key Decisions
- Boot scripts already write .squidsquad/{role}/.pid — leverage existing PID files
- Kill stale process before spawning replacement
- Grace period = 120s check on boot-attempts.log

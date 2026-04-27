# Iteration 379

- **Date**: 2026-04-27 01:08
- **Type**: active
- **Work Summary**:
  - Fixed #1470 QA rejection — test_missing_api_key_returns_2 wasn't mocking secrets file. API key found via shared_fs even after env var deleted. Now mocks both. 1076 tests green
  - 0 failures (pre-existing failure also fixed).
- **Notes**: none

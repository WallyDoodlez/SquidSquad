"""Regression tests for #13564 — cycle-input diet: cycle_pre.py's `_gh_fetch`
embedded full GitHub label objects (id/name/description/color per label per
issue) verbatim into every item it returns, and `_item_latest_comment`
embedded the full latest-comment body with no cap. Both flow straight into
cycle-input.json, the file every agent reads every cycle: measured on the
live open-issue set (150 squidsquad-labeled issues), the raw payload for
PM's primary fetch was 278KB, dominated by this ballast.

Fix:
- `_gh_fetch` now reduces each item's `labels` to a bare list of name
  strings (the only field any consumer reads — see `_item_label_names`) --
  measured 278KB -> 58KB (78.6% reduction) on the same live issue set.
- `_item_latest_comment` / `_enrich_with_comments` now cap the embedded
  comment body at `COMMENT_BODY_CAP_CHARS` (500) with an explicit
  truncation suffix; the forge-read pattern already mandates reading the
  issue before acting, so the full body in cycle-input was redundant.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_pre


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


@pytest.fixture(autouse=True)
def _clear_gh_fetch_cache():
    cycle_pre._GH_FETCH_CACHE.clear()
    yield
    cycle_pre._GH_FETCH_CACHE.clear()


# ---------------------------------------------------------------------------
# Label ballast stripping
# ---------------------------------------------------------------------------

class TestGhFetchStripsLabelBallast13564:
    def test_full_label_objects_reduced_to_bare_names(self, monkeypatch):
        raw_items = [{
            "number": 1, "title": "Some issue",
            "labels": [
                {"id": "LA_1", "name": "squidsquad", "description": "Managed", "color": "1d1d1d"},
                {"id": "LA_2", "name": "role:skill", "description": "Skill agent", "color": "1d76db"},
            ],
        }]
        monkeypatch.setattr(
            cycle_pre, "_run",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(raw_items)),
        )
        result = cycle_pre._gh_fetch("squidsquad", "open")
        assert result[0]["labels"] == ["squidsquad", "role:skill"]

    def test_no_id_description_color_survive(self, monkeypatch):
        raw_items = [{
            "number": 1, "title": "Some issue",
            "labels": [{"id": "LA_1", "name": "squidsquad", "description": "x", "color": "y"}],
        }]
        monkeypatch.setattr(
            cycle_pre, "_run",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(raw_items)),
        )
        result = cycle_pre._gh_fetch("squidsquad", "open")
        label = result[0]["labels"][0]
        assert isinstance(label, str)
        assert label == "squidsquad"

    def test_empty_labels_list_unaffected(self, monkeypatch):
        raw_items = [{"number": 1, "title": "No labels", "labels": []}]
        monkeypatch.setattr(
            cycle_pre, "_run",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(raw_items)),
        )
        result = cycle_pre._gh_fetch("squidsquad", "open")
        assert result[0]["labels"] == []

    def test_item_order_and_count_unchanged(self, monkeypatch):
        raw_items = [
            {"number": i, "title": f"Issue {i}",
             "labels": [{"id": f"LA_{i}", "name": "squidsquad"}]}
            for i in range(5)
        ]
        monkeypatch.setattr(
            cycle_pre, "_run",
            lambda cmd, **kw: _mock_result(stdout=json.dumps(raw_items)),
        )
        result = cycle_pre._gh_fetch("squidsquad", "open")
        assert [i["number"] for i in result] == [0, 1, 2, 3, 4]


class TestItemLabelNamesReadsBareStrings13564:
    def test_role_and_status_resolution_from_bare_names(self):
        item = {"labels": ["squidsquad", "role:skill", "status:approved"]}
        names = cycle_pre._item_label_names(item)
        assert names == {"squidsquad", "role:skill", "status:approved"}
        assert cycle_pre._item_has_label(item, "status:approved")
        assert cycle_pre._item_has_role(item, "skill")

    def test_missing_labels_key_returns_empty_set(self):
        assert cycle_pre._item_label_names({}) == set()


# ---------------------------------------------------------------------------
# Comment body capping
# ---------------------------------------------------------------------------

class TestCommentBodyCapped13564:
    def test_short_body_unchanged(self):
        assert cycle_pre._cap_comment_body("short body") == "short body"

    def test_body_at_exact_cap_unchanged(self):
        body = "x" * cycle_pre.COMMENT_BODY_CAP_CHARS
        assert cycle_pre._cap_comment_body(body) == body

    def test_long_body_truncated_with_suffix(self):
        body = "x" * (cycle_pre.COMMENT_BODY_CAP_CHARS + 200)
        capped = cycle_pre._cap_comment_body(body)
        assert len(capped) == cycle_pre.COMMENT_BODY_CAP_CHARS + len(cycle_pre._COMMENT_TRUNCATION_SUFFIX)
        assert capped.startswith("x" * cycle_pre.COMMENT_BODY_CAP_CHARS)
        assert capped.endswith(cycle_pre._COMMENT_TRUNCATION_SUFFIX)

    def test_item_latest_comment_caps_inline_comment_body(self):
        long_body = "y" * 900
        item = {"comments": [
            {"author": {"login": "human"}, "body": long_body, "createdAt": "2026-01-01T00:00:00Z"},
        ]}
        result = cycle_pre._item_latest_comment(item)
        assert len(result["body"]) == cycle_pre.COMMENT_BODY_CAP_CHARS + len(cycle_pre._COMMENT_TRUNCATION_SUFFIX)
        assert result["body"].endswith(cycle_pre._COMMENT_TRUNCATION_SUFFIX)
        assert result["author"] == "human"

    def test_item_latest_comment_short_body_untouched(self):
        item = {"comments": [
            {"author": {"login": "human"}, "body": "short", "createdAt": "2026-01-01T00:00:00Z"},
        ]}
        result = cycle_pre._item_latest_comment(item)
        assert result["body"] == "short"

    def test_enrich_with_comments_caps_legacy_path(self, monkeypatch):
        long_body = "z" * 900
        monkeypatch.setattr(
            cycle_pre, "_fetch_latest_comment",
            lambda n: {"author": "human", "body": long_body, "createdAt": "2026-01-01T00:00:00Z"},
        )
        items = [{"number": 1}]
        cycle_pre._enrich_with_comments(items)
        comment = items[0]["latest_comment"]
        assert len(comment["body"]) == cycle_pre.COMMENT_BODY_CAP_CHARS + len(cycle_pre._COMMENT_TRUNCATION_SUFFIX)
        assert comment["body"].endswith(cycle_pre._COMMENT_TRUNCATION_SUFFIX)

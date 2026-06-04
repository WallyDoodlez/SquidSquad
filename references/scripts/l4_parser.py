"""L4 single-file H2-slot + H3-op grammar parser (#10488, PRD-A Story A2b).

Pure-Python parser for ``.squidsquad/project/<role-class>.md``. Returns
a structured ``L4Document`` exposing per-slot lists of ``L4Op`` records
(op_type, target_step_id, body_text, parsed metadata trailer).

Grammar (TRD §3.3 + §7.3):
- ``## <Slot>``       — slot section (one of the six legal slot names).
- ``### append``      — append op (no target).
- ``### replace``     — whole-slot replace (no target).
- ``### replace step:cycle/<id>``       — step-targeted replace.
- ``### insert-before step:cycle/<id>`` — step-targeted insert-before.
- ``### insert-after  step:cycle/<id>`` — step-targeted insert-after.

Each H3 op may end with an HTML-comment metadata trailer carrying
``authored-by`` / ``authored-at`` / ``source-conversation`` lines. The
trailer is parsed into ``L4Op.metadata`` and stripped from
``body_text``.

A2b only owns the grammar. Per-slot constraint validation (vault
rejection, append-must-cite-sub-skill, mixed-op rejection, step-id
resolution against L1-L3) is A2's job; this parser does NOT enforce
those rules. It does reject H3 lines that don't match the op grammar
above — that's the "malformed H3 op" AC bullet.

Pure additive. v1 compose.py read sites are untouched.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


LEGAL_SLOTS = frozenset(
    {"identity", "responsibility", "soul", "instructions", "project-context", "vault"}
)

# ``## Slot Name`` — captures the slot text. The closing ``#`` count
# variant ``## Slot Name ##`` is also legal markdown; tolerate it.
_H2_RE = re.compile(r"^##\s+(.+?)\s*#*\s*$")
# ``### op [step:cycle/<id>]`` — the legal op grammar.
_H3_RE = re.compile(r"^###\s+(.+?)\s*#*\s*$")
# H3 op heading body. Strict: the heading text after ``### `` must match
# one of the five legal shapes verbatim.
_OP_RE = re.compile(
    r"^(append|replace)$"
    r"|^(replace|insert-before|insert-after)\s+step:cycle/([A-Za-z0-9_-]+)$"
)
# #10987: an H3 ``looks like'' an op if its heading begins with a reserved
# op keyword followed by whitespace or end-of-string. Op-like H3s parse
# strictly via ``_OP_RE`` — a near-miss like ``### replace step:cycle/``
# (missing id) raises a malformed-op diagnostic so user typos still fail
# loud. Non-op-like H3s (``### Zero-gap gate``, ``### Boot & Pre-flight``)
# are content sub-headings, not directives, and flow into the slot's
# implicit append body. Without this distinction, hand-authored L4 files
# under ``.squidsquad/project/`` cannot use H3 prose under ``## Soul`` /
# ``## Instructions`` etc. — which is how every shipped L4 file in
# production is structured.
_OP_LIKE_RE = re.compile(r"^(append|replace|insert-before|insert-after)(\s|$)")
# HTML-comment metadata trailer: ``<!-- key: value\n... -->`` at the end
# of an H3 body. Multiple key:value lines allowed. Both ``<!--`` and
# ``-->`` must be on their own lines for the trailer to count; comments
# elsewhere in the body are ignored. ``\Z`` anchors at end-of-string
# (NOT ``$`` with MULTILINE, which would treat any mid-body ``-->\n``
# as the trailer). ``\A`` lets the trailer be the entire body (an H3
# op whose only content is the metadata block).
# ``(?!<!--)[\s\S]`` inside the captured group forbids another ``<!--``
# from sneaking in — combined with ``\Z`` at the tail, this anchors on
# the LAST ``<!--`` block, not the first. Without the negative
# lookahead, a multi-line mid-body comment followed by a real trailer
# would be wrongly absorbed (DS finding 1).
_TRAILER_RE = re.compile(
    r"(?:\A|\n)<!--\s*\n((?:(?!<!--)[\s\S])*?)\n\s*-->\s*\Z",
)
_METADATA_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:\s*(.*)$")


class L4ParseError(ValueError):
    """Raised when the file violates the H2/H3 grammar."""


@dataclass
class L4Op:
    op_type: str  # "append" | "replace" | "insert-before" | "insert-after"
    target_step_id: str | None  # None for `append` or whole-slot `replace`
    body_text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class L4Document:
    slots: dict = field(default_factory=dict)  # slot_name -> list[L4Op]

    @classmethod
    def empty(cls):
        return cls(slots={})


def parse_l4_file(path):
    """Parse ``path`` into an ``L4Document``. Missing file → empty doc.

    Raises ``L4ParseError`` on:
    - Unknown slot name in an ``## <Slot>`` heading.
    - H3 heading text that doesn't match the legal op grammar.
    - H3 op appearing outside any slot.
    """
    path = Path(path)
    if not path.is_file():
        return L4Document.empty()
    text = path.read_text(encoding="utf-8")
    return _parse_text(text, source=str(path))


def parse_l4_text(text, source="<text>"):
    """Parse raw text. Used by tests; same semantics as ``parse_l4_file``."""
    return _parse_text(text, source=source)


def _parse_text(text, source):
    slots = {}
    current_slot = None
    current_op = None
    current_body = []  # lines accumulating for the current H3 op

    def _commit_current_op():
        nonlocal current_op
        if current_op is None:
            return
        # The trailer regex tolerates both ``\A<!--`` and ``\n<!--``
        # prefixes (see _TRAILER_RE), so stripping both leading and
        # trailing newlines here is safe and produces a clean body for
        # ops that have prose before the trailer.
        body = "\n".join(current_body).strip("\n")
        metadata, body = _extract_metadata(body)
        # An implicit-append op with an empty body adds nothing — skip
        # it so an empty ``## Soul`` slot doesn't show up as a soul
        # append-op with no content (the L1-L3 soul stays unchanged).
        if not (current_op.op_type == "append"
                and current_op.target_step_id is None
                and not body
                and not metadata
                and getattr(current_op, "_implicit", False)):
            current_op.body_text = body
            current_op.metadata = metadata
            slots.setdefault(current_slot, []).append(current_op)
        current_op = None

    def _open_implicit_append():
        """#10987: non-instructions slots use H3 as content sub-headings,
        not as op directives. Open an implicit ``append`` op when entering
        such a slot so subsequent content (including H3 sub-headings)
        flows into a single append body.
        """
        nonlocal current_op, current_body
        op = L4Op(op_type="append", target_step_id=None, body_text="")
        # Mark for the empty-body skip in _commit_current_op so a slot
        # heading with no body doesn't manifest as a no-op append entry.
        op._implicit = True
        current_op = op
        current_body = []

    lines = text.splitlines()
    for lineno, raw in enumerate(lines, start=1):
        h2 = _H2_RE.match(raw) if raw.startswith("## ") else None
        h3 = _H3_RE.match(raw) if raw.startswith("### ") else None

        if h2 is not None:
            _commit_current_op()
            current_body = []
            slot_name = _normalize_slot(h2.group(1))
            if slot_name not in LEGAL_SLOTS:
                raise L4ParseError(
                    f"{source}:{lineno}: unknown L4 slot heading "
                    f"`## {h2.group(1)}` — must be one of "
                    f"{sorted(LEGAL_SLOTS)}."
                )
            current_slot = slot_name
            slots.setdefault(current_slot, [])
            # #10987: every slot opens an implicit append at the ``## <Slot>``
            # boundary. This single rule covers three otherwise-separate
            # edge cases: (a) prose H3 sub-headings (DM SOUL etc.), (b)
            # plain prose between the slot heading and the first H3, (c)
            # prose H3 sub-headings appearing AFTER an explicit op
            # (without this, the prose H3 would be absorbed into the
            # explicit op's body instead of opening a fresh append).
            # The implicit op is suppressed by _commit_current_op when
            # its body+metadata are empty, so an explicit ``### <op>``
            # immediately following the slot heading still produces the
            # explicit op without a leading no-op implicit alongside it.
            _open_implicit_append()
            continue

        if h3 is not None:
            heading = h3.group(1).strip()
            if current_slot is None:
                raise L4ParseError(
                    f"{source}:{lineno}: H3 op `### {heading}` appears "
                    f"outside any slot — H3 ops MUST follow a `## <Slot>` "
                    f"heading."
                )
            # #10987: H3 lines are op directives only when they ``look
            # like'' ops (start with a reserved op keyword followed by
            # whitespace or end-of-string). Op-like headings parse
            # strictly — malformed forms still raise a diagnostic.
            # Non-op-like headings are prose sub-headings and flow into
            # the slot's implicit append body. ``_open_implicit_append``
            # already ran at the ``## <Slot>`` boundary, so the current
            # op exists; if a prose H3 lands after an explicit op was
            # just opened, commit the explicit op and open a fresh
            # implicit so the prose isn't absorbed into the explicit
            # body.
            if _OP_LIKE_RE.match(heading) is None:
                if current_op is not None and not getattr(
                    current_op, "_implicit", False,
                ):
                    _commit_current_op()
                    _open_implicit_append()
                current_body.append(raw)
                continue
            _commit_current_op()
            current_body = []
            op_type, target = _parse_h3_op(heading, source, lineno)
            current_op = L4Op(
                op_type=op_type, target_step_id=target, body_text="",
            )
            continue

        if current_op is not None:
            current_body.append(raw)

    _commit_current_op()
    return L4Document(slots=slots)


def _parse_h3_op(heading, source, lineno):
    m = _OP_RE.match(heading)
    if m is None:
        raise L4ParseError(
            f"{source}:{lineno}: malformed H3 op heading `### {heading}`. "
            f"Expected one of: `### append`, `### replace`, "
            f"`### replace step:cycle/<id>`, `### insert-before step:cycle/<id>`, "
            f"`### insert-after step:cycle/<id>`."
        )
    if m.group(1) is not None:
        # ``append`` or whole-slot ``replace``.
        return m.group(1), None
    return m.group(2), m.group(3)


def _normalize_slot(raw):
    """Lowercase + hyphenate the slot label. ``Project Context`` -> ``project-context``."""
    return re.sub(r"\s+", "-", raw.strip().lower())


def _extract_metadata(body):
    """Split off the HTML-comment metadata trailer, returning ``(metadata, body)``.

    If no trailer is present, returns ``({}, body)`` unchanged.
    """
    m = _TRAILER_RE.search(body)
    if m is None:
        return {}, body
    metadata = {}
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line:
            continue
        km = _METADATA_KEY_RE.match(line)
        if km is None:
            continue  # unparseable line — ignore per "compose does not require or validate" (TRD §7.3)
        metadata[km.group(1)] = km.group(2).strip()
    # body[:m.start()] is the correct slice whether the regex matched
    # at \A (start=0) or after a \n (start at the newline before <!--).
    body = body[: m.start()].rstrip("\n")
    return metadata, body

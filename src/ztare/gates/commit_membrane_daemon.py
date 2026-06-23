"""commit_membrane_daemon.py — GP-241 epistemic-verificator daemon.

OBSERVE-MODE Phase-1 (2026-05-17). The verificator: it is the SOLE
writer of the official store; agents only drop proposal JSON into the
queue. It runs `commit_membrane_gate.evaluate` and either stamps an
official record (pass) or files a quarantine record (fail). It never
trusts the agent to have run the gate — running it is the daemon's job.

ROOT-OF-TRUST HONESTY (GP-241 v4 + cold GPT-5.5 pass):
- The official store is OUTSIDE the agent-writable repo
  ($ZTARE_OFFICIAL_STORE, default ~/ztare_official_store) — per the
  spec's explicit rule "do not put the official store inside the
  agent-writable repo." Store LOCATION + daemon-sole-writer is the
  boundary; NOT chowning the live repo (that would break the dev
  machine and is not what the design asks).
- True multi-user OS separation (separate ztare_verify user, perms) is
  the PRODUCTION/VPS hardening step, deliberately NOT applied to a live
  single-user dev machine. Until that exists this is OBSERVE-MODE: it
  proves the machinery and stamps authoritatively, but it does not yet
  physically prevent a non-daemon process from writing the store. That
  limitation is stated, not laundered.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from ztare.gates.commit_membrane_gate import evaluate
from ztare.common.paths import REPO_ROOT

STORE = Path(os.environ.get(
    "ZTARE_OFFICIAL_STORE", str(Path.home() / "ztare_official_store")))
INBOX = STORE / "proposal_queue" / "inbox"
OFFICIAL = STORE / "official"
QUARANTINE = STORE / "quarantine"
LEDGER = OFFICIAL / "transitions.stamped.jsonl"
# Daemon-invoked judge worker queue (GP-241 #2). requests: written
# ONLY by the daemon (ztare_verify), read by the ztare_judge worker.
# verdicts: written ONLY by the worker (ztare_judge), read by the
# daemon. Ownership/perms are set by the deploy script (root); the
# agent has NO access to either dir (it cannot forge a request nor
# inject a verdict). _ensure() only mkdirs as a safety net.
JUDGE_Q = STORE / "judge_queue"
JREQ = JUDGE_Q / "requests"
JVERD = JUDGE_Q / "verdicts"
# Daemon-owned consumed-marker dir. The daemon can READ but NOT write
# JVERD (judge-owned, so the agent cannot inject verdicts) ⇒ it must
# NOT unlink verdict files. Idempotency is a marker the daemon owns.
JING = JUDGE_Q / "ingested"

GATE_VERSION = "commit_membrane_gate/v4-witness"

FORMAL_CLAIM_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\b(clay|millennium[- ]problem|navier[- ]stokes)\b.{0,100}"
        r"\b(proved|proven|solved|resolved|closed|settled|closure|qed)\b",
        r"\b(proved|proven|solved|resolved|closed|settled|closure)\b.{0,100}"
        r"\b(clay|millennium[- ]problem|navier[- ]stokes)\b",
        r"\b(formal|compiled)\s+proof\b",
        r"\b(theorem|lean)\b.{0,100}"
        r"\b(proves|proved|proven|settles|solves|closes|closure)\b",
        r"\b(proves|proved|proven|settles|solves|closes)\b.{0,100}"
        r"\b(theorem|lean)\b",
        r"\b(qed|sorry-free|axiom-free|target_statement_hash)\b",
        r"∎",
    )
)


def _formal_claim_tripwire(text: str) -> str | None:
    for pattern in FORMAL_CLAIM_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure() -> None:
    for d in (INBOX, OFFICIAL, QUARANTINE, JUDGE_Q, JREQ, JVERD, JING):
        d.mkdir(parents=True, exist_ok=True)


def _ledger_rows_raw() -> list[dict]:
    """All parseable ledger rows (used for duplicate-pid rejection —
    cold re-review blocker #1)."""
    out: list[dict] = []
    if not LEDGER.is_file():
        return out
    for ln in LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def _daemon_manifest(tick_id: str, kind: str) -> "Path":
    """cold review b5upqb5kz F1: the close MUST read the DAEMON-OWNED
    manifest bytes (written by the manifest_receipt handler from the
    bytes the receipt carried), NOT the agent's local repo path which
    on a remote-enforce VPS may never have existed. Co-located
    fallback to the repo path only if no daemon copy exists (legacy
    same-host runs)."""
    _d = OFFICIAL / "manifests" / f"{tick_id}.{kind}.json"
    if _d.is_file():
        return _d
    return (REPO_ROOT / "analytics" / "public" / kind / tick_id
            / f"{kind}_manifest.json")


def _re_hex64(s: str) -> bool:
    # cold review b5upqb5kz F6: EXACTLY 64 hex (a full SHA-256) — an
    # 8-hex prefix space is collision-weak for a Clay-target anchor.
    import re as _re
    return bool(_re.fullmatch(r"[0-9a-fA-F]{64}", str(s or "")))


def _registered_targets() -> set[str]:
    """R5''' provenance: the set of statement hashes the OPERATOR
    registered via CHAIN-VALID daemon-signed `target_register` rows.
    Tamper-evident — an agent-written registry json is NOT trusted
    (that path is removed from the gate). Empty if unavailable ⇒
    closure claims fail-closed."""
    try:
        from ztare.gates.stamped_state import chain_valid, _rows
        valid, _ = chain_valid(_rows())
    except Exception:
        return set()
    return {str(r.get("statement_sha256", "")).lower()
            for r in valid
            if r.get("transition_type") == "target_register"
            and r.get("statement_sha256")}


def _registered_target_row(stmt_sha256: str) -> dict | None:
    """C3: the CHAIN-VALID daemon-signed target_register row for a
    given statement hash, carrying the registered statement_text +
    env_hash for the Lean-kernel defeq probe. None ⇒ not registered
    (caller fail-closes)."""
    try:
        from ztare.gates.stamped_state import chain_valid, _rows
        valid, _ = chain_valid(_rows())
    except Exception:
        return None
    h = str(stmt_sha256 or "").lower()
    for r in valid:
        if (r.get("transition_type") == "target_register"
                and str(r.get("statement_sha256", "")).lower() == h):
            return r
    return None


def _manifest_receipt_ok(tick_id: str, kind: str,
                         file_sha256: str) -> bool:
    """R2: True iff a CHAIN-VALID daemon-SIGNED `manifest_receipt`
    exists for (tick_id, kind) whose recorded manifest_sha256 equals
    file_sha256 (the hash of the manifest the daemon is reading NOW).
    A forged COMPLETE flag or post-receipt tampering ⇒ no match ⇒
    fail-closed. The agent cannot forge daemon_sig.

    Cold review bq4z7midf F3: use FULL chain_valid (recompute body +
    parent chain), not signature-over-official_state_hash alone — a
    valid sig on a row whose body/parent was tampered must NOT count.
    Fail-closed if chain_valid is unavailable."""
    try:
        from ztare.gates.stamped_state import chain_valid, _rows
        valid, _errs = chain_valid(_rows())
    except Exception:
        return False
    for r in valid:
        if (r.get("transition_type") == "manifest_receipt"
                and str(r.get("tick_id", "")) == str(tick_id)
                and str(r.get("manifest_kind", "")) == str(kind)
                and str(r.get("manifest_sha256", "")) == str(file_sha256)):
            return True
    return False


def _canon_wsha(witness: dict) -> str:
    """Witness sha — EXACTLY the canonicalization the judge_verdict
    handler (D3) and the resolver use: drop `provenance`, sorted keys,
    ensure_ascii=False. One definition, three consumers."""
    w = {k: v for k, v in (witness or {}).items() if k != "provenance"}
    return hashlib.sha256(json.dumps(
        w, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()


def _already_judged(tick_id: str, contract_id: str, item_id: str,
                    wsha: str) -> bool:
    """True iff a chain-valid PASS judge_verdict for this exact
    (tick,contract,item,witness) already exists — don't re-request.
    cold review bxu2w8voa R1: use CHAIN-VALID rows (same set the
    resolver trusts), not raw rows — a bad raw row must not suppress
    request emission while the resolver still refuses discharge."""
    try:
        from ztare.gates.stamped_state import chain_valid, _rows
        rows, _ = chain_valid(_rows())
    except Exception:
        rows = []
    for r in rows:
        if (r.get("transition_type") == "judge_verdict"
                and str(r.get("verdict", "")).strip().lower() == "pass"
                and item_id in (r.get("bound_obligations") or [])
                and str(r.get("tick_id")) == str(tick_id)
                and str(r.get("contract_id")) == str(contract_id)
                and str(r.get("witness_sha")) == str(wsha)):
            return True
    return False


def _emit_judge_request(*, tick_id: str, contract_id: str,
                        item_id: str, goal: str, stt: str,
                        declared_signals: dict, witness: dict) -> str:
    """GP-241 #2: the DAEMON (sole writer of judge_queue/requests)
    pins a judge_request from the FROZEN start contract + the agent's
    submitted witness and daemon-signs it. The ztare_judge worker
    cannot be steered by the agent (it only services daemon-signed
    requests; the agent has no write access here). Idempotent: one
    request per (tick,contract,item,witness). Returns a status str."""
    wsha = _canon_wsha(witness)
    try:
        from ztare.surfacing.pre_tick_obligation_compiler import (
            judge_prompt_for,
        )
        _prompt = judge_prompt_for(
            goal, stt, declared_signals or {}, item_id,
            {k: v for k, v in (witness or {}).items()
             if k != "provenance"})
        _phash = hashlib.sha256(
            _prompt.encode("utf-8")).hexdigest()[:16] if _prompt else "noprompt"
    except Exception:
        _phash = "prompt_error"
    rid = hashlib.sha256(
        f"{tick_id}|{contract_id}|{item_id}|{wsha}|{_phash}".encode()
        ).hexdigest()[:16]
    target = JREQ / f"{rid}.json"
    if target.exists():
        return f"request {rid} already queued"
    if _already_judged(tick_id, contract_id, item_id, wsha):
        return f"already judged {rid}"
    payload = {
        "kind": "judge_request", "req_id": rid, "ts": _now(),
        "tick_id": tick_id, "contract_id": contract_id,
        "item_id": item_id, "goal": goal,
        "start_transition_type": stt,
        "start_declared_signals": declared_signals or {},
        "witness": {k: v for k, v in (witness or {}).items()
                    if k != "provenance"},
        "witness_sha": wsha,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    from ztare.gates._daemon_sig import sign as _sgn
    rec = {"payload": payload,
           "daemon_sig": _sgn(hashlib.sha256(
               canonical.encode("utf-8")).hexdigest())}
    tmp = JREQ / f".{rid}.tmp"
    tmp.write_text(json.dumps(rec), encoding="utf-8")
    tmp.replace(target)
    return f"emitted judge_request {rid}"


def _ingest_verdicts() -> None:
    """Move ztare_judge-worker-produced verdicts into the inbox as
    judge_verdict proposals so the existing hardened+kill-tested
    handler stamps them. The agent has NO access to JVERD; only the
    daemon (which owns the inbox) relays. Hostile-input hardened:
    regular file, size cap, dict with a judge_verdict `close`."""
    if not JVERD.is_dir():
        return
    JING.mkdir(parents=True, exist_ok=True)
    for f in sorted(JVERD.glob("*.json")):
        marker = JING / f"{f.stem}.done"
        if marker.exists():
            continue  # already relayed (the daemon CANNOT delete the
            # judge-owned source; the marker it owns is the dedupe).
        try:
            if f.is_symlink() or not f.is_file():
                raise ValueError("not a regular file")
            if f.stat().st_size > 256 * 1024:
                raise ValueError("oversize")
            d = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(d, dict):
                raise ValueError("not an object")
            close = d.get("close")
            if (not isinstance(close, dict)
                    or not str(close.get("judge_sig", "")).strip()):
                raise ValueError("not a judge_verdict close")
            # cold review bxu2w8voa R2: DETERMINISTIC pid per verdict
            # file (constant, regex-valid). Mark done ONLY once a
            # chain-valid ledger row carries this pid (i.e. the handler
            # actually STAMPED it). If a relay quarantines on a
            # transient (e.g. key/anchor) failure it is NOT marked ⇒
            # re-relayed next scan with the SAME pid until it stamps —
            # no lost verdict, and no duplicate stamp (once stamped the
            # pid is in the ledger so the chain-valid check marks it
            # and stops, and process_one duplicate-rejects the pid).
            pid = ("20260101T000000_"
                   + hashlib.sha256(f.stem.encode()).hexdigest()[:8])
            try:
                from ztare.gates.stamped_state import (
                    chain_valid as _cv, _rows as _rw)
                _vrows, _ = _cv(_rw())
            except Exception:
                _vrows = []
            if any(str(r.get("proposal_id")) == pid for r in _vrows):
                marker.write_text(pid, encoding="utf-8")  # stamped
                continue
            prop = {"proposal_id": pid,
                    "transition_type": "judge_verdict",
                    "agent_runtime": "ztare_judge_worker",
                    "goal": f"judge {close.get('item_id')}",
                    "transition_text": "out-of-loop judge verdict",
                    "close": close}
            itmp = INBOX / f".{pid}.tmp"
            itmp.write_text(json.dumps(prop), encoding="utf-8")
            itmp.replace(INBOX / f"{pid}.json")
            # NO marker here — only after it is stamped (next scan).
        except Exception as e:
            (QUARANTINE / f"{f.stem}.verdict_reject.json").write_text(
                json.dumps({"ts": _now(), "verdict_file": f.name,
                            "reason": f"bad worker verdict: {e}"}))
            # terminal (deterministic given the file) — mark so the
            # daemon does not reprocess; never unlink the judge-owned
            # source.
            marker.write_text(f"reject:{e}", encoding="utf-8")


def _parent_hash() -> str:
    """CHAIN-FORMAT FIX (codex confirm 2026-05-17, sev-4 liveness
    blocker): the reader (stamped_state.official_transitions) chains on
    each row's `official_state_hash`. The writer MUST use the same:
    parent = the LAST row's official_state_hash (NOT hash(raw line) —
    that disagreed with the reader, so the chain was invalid from
    row 2 and nothing validated). 'GENESIS' if no/empty/unparseable
    ledger (first row)."""
    if not LEDGER.is_file():
        return "GENESIS"
    parent = "GENESIS"
    for ln in LEDGER.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            h = json.loads(ln).get("official_state_hash")
            if h:
                parent = h
        except Exception:
            continue
    return parent


def process_one(proposal_path: Path) -> dict:
    """Gate one proposal. Pass ⇒ stamped row appended to the official
    hash-chained ledger. Fail ⇒ quarantine record. Returns the verdict."""
    # INBOX HARDENING (codex sev-4): the inbox is agent-writable —
    # treat contents as hostile. Reject symlinks / non-regular files
    # (no symlink-follow into the official store or arbitrary paths),
    # cap size (no memory-exhaustion proposal), and require a dict
    # schema. Any of these ⇒ quarantine, never process.
    _MAX = 256 * 1024
    _PID_RE = __import__("re").compile(
        r"^[0-9]{8}T[0-9]{6}_[0-9a-f]{8}$")
    try:
        if proposal_path.is_symlink() or not proposal_path.is_file():
            raise ValueError("not a regular file (symlink/special)")
        if proposal_path.stat().st_size > _MAX:
            raise ValueError(f"oversize > {_MAX} bytes")
        # cold round-3 caveat: hash the RAW BYTES (not a
        # decode→re-encode round-trip) so "bound to the exact submitted
        # bytes" is literally true and cannot drift on non-canonical
        # utf-8 / BOM. propose.py hashes body.encode("utf-8") = exactly
        # the bytes it writes; subprocess writes those bytes verbatim.
        raw_bytes = proposal_path.read_bytes()
        raw = raw_bytes.decode("utf-8")
        # COLD RE-REVIEW BLOCKER #1 (proposal_id relabel forge). The
        # canonical identity is the INBOX FILENAME STEM (propose.py
        # names it <pid>.json, pid regex-pinned), NOT the agent-
        # supplied JSON field, AND the exact submitted bytes are
        # hashed into the row. The poll matches on pid AND body sha,
        # so "submit good B carrying bad A's pid" cannot make A
        # official (B's row has B's body hash, not A's).
        body_sha = hashlib.sha256(raw_bytes).hexdigest()
        pid = proposal_path.stem
        if not _PID_RE.match(pid):
            raise ValueError(f"filename stem not a valid pid: {pid!r}")
        p = json.loads(raw)
        if not isinstance(p, dict):
            raise ValueError("proposal is not a JSON object")
        if p.get("proposal_id") != pid:
            raise ValueError(
                f"proposal_id field {p.get('proposal_id')!r} != "
                f"filename {pid!r} (relabel attempt)")
        for _r in _ledger_rows_raw():
            if _r.get("proposal_id") == pid:
                raise ValueError(f"duplicate proposal_id {pid} "
                                 f"already in ledger (replay/relabel)")
    except Exception as e:
        rec = {"ts": _now(), "proposal": proposal_path.name,
               "verdict": "reject", "reason": f"hostile/unparseable: {e}"}
        (QUARANTINE / f"{proposal_path.stem}.reject.json").write_text(
            json.dumps(rec, indent=2))
        proposal_path.unlink(missing_ok=True)
        return rec

    text = str(p.get("transition_text", ""))
    declared = p.get("declared", {}) if isinstance(p.get("declared"), dict) else {}

    # ── FORCED-CLOSE TRANSACTION (2-cold-pass synthesis 2026-05-17).
    # Authority inversion: a `tick_close` is a daemon-OWNED transition.
    # The agent submits structured close fields; the DAEMON validates
    # and (post-sign) materializes the official F-row itself — agent-
    # written EXPERIMENT_TRACK_RECORD rows are graffiti, not authority
    # (reverse-H3). Additive: the battle-tested result/closure stamp
    # path is untouched; this only adds requirements for the new type.
    # ── JUDGE_VERDICT TRANSACTION (cold-review bbx3cuw8s: the JUDGE
    # half of mutator→JUDGE→monitor). A separate cross-FAMILY judge
    # emits its obligation verdict here; the daemon signs it bound to
    # {tick_id,contract_id,item_id,witness_sha,verdict,judge_identity}.
    # _resolve_provenance('judge:<this id>') then discharges the
    # mutator's substantive obligation. The judge family is bound to a
    # COMMITTED anchor (deploy/gp241_family_anchors.json) via the
    # judge-KEY-signed model_identity — never a proposal-declared
    # mutator family (cold review boibujil4 D1).
    if str(p.get("transition_type", "")) == "judge_verdict":
        jv = p.get("close") if isinstance(p.get("close"), dict) else {}
        need = ("tick_id", "contract_id", "item_id", "witness_sha",
                "verdict", "judge_identity", "judge_sig", "proof_msg",
                "prompt_hash")
        miss = [k for k in need if not str(jv.get(k, "")).strip()]
        # cold review boibujil4 D1: the mutator family is NEVER read
        # from the proposal (attacker-controlled `agent_runtime`).
        # Both families are COMMITTED anchors (deploy/
        # gp241_family_anchors.json), same trust class as the judge
        # pubkey. None => fail-closed (anchors missing/invalid/equal).
        from ztare.gates._daemon_sig import (
            canon_family, load_family_anchors)
        _anchors = load_family_anchors()
        bad = list(miss)
        if _anchors is None:
            bad.append("GP-241 family anchors unprovisioned/invalid "
                       "(deploy/gp241_family_anchors.json) — judge "
                       "cross-family unverifiable (fail-closed)")
        jud_fam = "unknown"
        if str(jv.get("verdict", "")).strip().lower() not in (
                "pass", "fail"):
            bad.append("verdict must be 'pass' or 'fail'")
        # NOTE: the cross-family check is done below against the
        # judge-KEY-SIGNED model_identity (cold review b1djdevru C) —
        # the proposal-supplied judge_identity is NOT trusted here.
        # cold review baxgapbe9: PROVE a real separate judge ran. The
        # judge_sig must be a valid JUDGE-KEY signature over proof_msg
        # (mutator lacks the judge key ⇒ cannot fabricate). And the
        # daemon RECOMPUTES the obligation prompt un-forgeably; the
        # proof's prompt_hash MUST match (no weakened-rubric feed).
        if not miss:
            try:
                from ztare.gates._daemon_sig import judge_verify
                pm = str(jv.get("proof_msg", ""))
                ok_sig = judge_verify(hashlib.sha256(
                    pm.encode("utf-8")).hexdigest(),
                    str(jv.get("judge_sig", "")))
                if not ok_sig:
                    bad.append("judge_sig not a valid JUDGE-KEY "
                               "signature over proof_msg — no proof a "
                               "real separate judge ran (forgeable "
                               "verdict rejected)")
                pj = json.loads(pm) if pm else {}
                # cold review b1djdevru (A): TOTAL signed-proof binding
                # — EVERY field the judge signed must equal the claimed
                # row, else a signed proof for tick A is replayable on
                # tick B. (The signed proof binds tick/contract/item;
                # checking only verdict/witness/prompt let replay
                # through.)
                _pairs = [
                    ("tick_id", jv.get("tick_id")),
                    ("contract_id", jv.get("contract_id")),
                    ("item_id", jv.get("item_id")),
                    ("witness_sha", jv.get("witness_sha")),
                    ("prompt_hash", jv.get("prompt_hash")),
                    ("artifact_sha", jv.get("artifact_sha", "")),
                    ("verdict", jv.get("verdict")),
                ]
                _mism = [k for k, v in _pairs
                         if str(pj.get(k)) != str(v)]
                if _mism:
                    bad.append(f"signed proof fields {_mism} disagree "
                               f"with the claimed judge_verdict "
                               f"(replay/substitution rejected)")
                # cold review boibujil4 D1: judge family from the
                # judge-KEY-SIGNED model_identity, checked against the
                # COMMITTED judge anchor (NOT a comparison to a
                # proposal-declared mutator family). load_family_anchors
                # already guaranteed judge != mutator and neither
                # 'unknown'; here we only bind the signed identity to
                # the judge anchor. canon_family is the strict enum
                # (no substring ambiguity).
                _signed_model = str(pj.get("model_identity", ""))
                jud_fam = canon_family(_signed_model)
                if str(jv.get("judge_identity")) != _signed_model:
                    bad.append("judge_identity != signed "
                               "model_identity (unsigned family claim)")
                if _anchors is not None and jud_fam != _anchors[0]:
                    bad.append(f"signed judge family {jud_fam!r} != "
                               f"committed judge anchor "
                               f"{_anchors[0]!r} (same-family / "
                               f"spoofed-family judge rejected)")
                # un-forgeable prompt binding: recompute from the
                # FROZEN, daemon-signed start_tick row for this tick_id
                # (the agent cannot weaken it), NOT agent-supplied
                # goal. judged_witness is the agent's discharge content
                # (legitimately agent-authored, pinned by witness_sha).
                from ztare.gates._daemon_sig import verify as _vs
                _sr = None
                for _r in _ledger_rows_raw():
                    if (_r.get("transition_type") == "start_tick"
                            and str(_r.get("tick_id"))
                            == str(jv.get("tick_id"))
                            and _vs(str(_r.get(
                                "official_state_hash", "")),
                                _r.get("daemon_sig"))):
                        _sr = _r
                        break
                if _sr is None:
                    bad.append("no frozen signed start_tick for this "
                               "judge_verdict's tick_id")
                else:
                    # cold review boibujil4 D2: the verdict's contract
                    # MUST be the one frozen at this tick's start
                    # (start_tick is immutable per tick_id ⇒ this
                    # uniquely pins the contract instance). A
                    # foreign-contract verdict is rejected.
                    if str(jv.get("contract_id")) != str(
                            _sr.get("contract_id", "")):
                        bad.append("judge_verdict contract_id != "
                                   "FROZEN start_tick contract_id "
                                   "(foreign-contract verdict "
                                   "rejected)")
                    # cold review boibujil4 D3: the witness the judge
                    # actually saw (judged_witness) MUST hash to the
                    # signed witness_sha — same canonicalization the
                    # producer and _resolve_provenance use. Otherwise a
                    # proof judged on witness X discharges witness Y.
                    _jw = {k: v for k, v in (
                        jv.get("judged_witness") or {}).items()
                        if k != "provenance"}
                    if hashlib.sha256(json.dumps(
                            _jw, sort_keys=True,
                            ensure_ascii=False).encode("utf-8")
                            ).hexdigest() != str(
                            jv.get("witness_sha")):
                        bad.append("judged_witness hash != signed "
                                   "witness_sha (judge saw a "
                                   "different witness than the one "
                                   "discharged)")
                    from ztare.surfacing\
                        .pre_tick_obligation_compiler \
                        import judge_prompt_for
                    exp = judge_prompt_for(
                        str(_sr.get("goal", "")),
                        str(_sr.get("start_transition_type", "")),
                        _sr.get("start_declared_signals") or {},
                        str(jv.get("item_id", "")),
                        jv.get("judged_witness") or {})
                    if not exp or hashlib.sha256(
                            exp.encode("utf-8")).hexdigest() != str(
                            jv.get("prompt_hash")):
                        bad.append("prompt_hash != prompt recomputed "
                                   "from the FROZEN start_tick "
                                   "contract (weakened-rubric feed "
                                   "rejected)")
            except Exception as e:
                bad.append(f"judge-proof verify error {type(e).__name__}")
        if bad:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "judge_verdict",
                   "verdict": "quarantine", "failed": bad}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        parent = _parent_hash()
        jrow = {
            "ts": _now(), "proposal_id": pid,
            "proposal_body_sha256": body_sha,
            "transition_type": "judge_verdict",
            "tick_id": str(jv["tick_id"]),
            "contract_id": str(jv["contract_id"]),
            "item_id": str(jv["item_id"]),
            "bound_obligations": [str(jv["item_id"])],
            "witness_sha": str(jv["witness_sha"]),
            "artifact_sha": str(jv.get("artifact_sha", "")),
            "verdict": str(jv["verdict"]).strip().lower(),
            "judge_identity": str(jv["judge_identity"]),
            "judge_family": jud_fam,
            "verifier_id": "commit_membrane_daemon",
            "gate_version": GATE_VERSION,
            "parent_state_hash": parent,
            "membrane_stamp": f"JUDGE:{jv['item_id']}",
            "verdict_kind": "judge_verdict",
        }
        _b = json.dumps(jrow, sort_keys=True)
        jrow["official_state_hash"] = hashlib.sha256(
            (parent + _b).encode()).hexdigest()[:32]
        from ztare.gates._daemon_sig import sign as _jsgn
        jrow["daemon_sig"] = _jsgn(jrow["official_state_hash"])
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(jrow) + "\n")
        proposal_path.unlink(missing_ok=True)
        return {"verdict": "pass", "proposal_id": pid,
                "transition_type": "judge_verdict",
                "official_state_hash": jrow["official_state_hash"],
                "judge_verdict": jrow["verdict"]}

    is_close = str(p.get("transition_type", "")) == "tick_close"
    close = p.get("close") if isinstance(p.get("close"), dict) else {}
    if is_close:
        # MECE contract layering (operator 2026-05-17). MUTUALLY
        # EXCLUSIVE × COLLECTIVELY EXHAUSTIVE:
        #   micro  = the TICK-SCOPED contract — MANDATORY, daemon-bound
        #            into THIS signed tick_close row (no longer merely
        #            print-mandatory in rd_tick_brief).
        #   meso/macro = own-horizon (multi-tick / 30d) — CONDITIONAL
        #            on what the tick entails, NEVER required to close a
        #            tick (post_tick_check already treats them as
        #            expected-open, not hard). They are therefore NOT
        #            tick_close-bound: a close claiming scope!=micro is
        #            a category error and is rejected.
        _scope = str(close.get("contract_scope", "micro")).strip().lower()
        _need = ("tick_id", "contract_id", "f_row_id", "f_row_body")
        _missing = [k for k in _need
                    if not str(close.get(k, "")).strip()]
        if _scope != "micro":
            _missing = _missing or []
            _missing.append(f"contract_scope must be 'micro' for a "
                            f"tick_close (got {_scope!r}; meso/macro are "
                            f"conditional own-horizon contracts, never "
                            f"tick-close-bound — MECE)")
        if _missing:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "tick_close", "verdict": "quarantine",
                   "failed": [f"tick_close missing structured close "
                              f"field(s): {_missing} — the daemon owns "
                              f"close; a thin client must submit them"]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        # FROZEN START-CONTRACT BINDING (pre-tick→contract migration,
        # 2026-05-17): "no signed start_tick contract → no close."
        # The pre-tick mandate is no longer print — it is a
        # daemon-minted signed `start_tick` row. A close REQUIRES a
        # chain-valid, daemon-SIGNED start_tick row whose tick_id ==
        # this close's tick_id. Kills the skip-start-tick attack.
        from ztare.gates._daemon_sig import verify as _vsig
        _tid = str(close["tick_id"])
        # cold review bxu2w8voa R4: one STAMPED tick_close per tick_id
        # (ledger hygiene). A quarantined first attempt leaves NO
        # chain-valid row, so the protocol's required re-submit is
        # unaffected; only a SECOND official close of an
        # already-closed tick is refused.
        try:
            from ztare.gates.stamped_state import (
                chain_valid as _cvc, _rows as _rwc)
            _cl_rows, _ = _cvc(_rwc())
        except Exception:
            _cl_rows = []
        if any(r.get("transition_type") == "tick_close"
               and str(r.get("tick_id")) == _tid for r in _cl_rows):
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "tick_close",
                   "verdict": "quarantine",
                   "failed": [f"tick_id {_tid!r} already has a "
                              f"chain-valid official tick_close — "
                              f"refusing a duplicate close (ledger "
                              f"hygiene; re-open a new tick_id)"]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        # cold review bq4z7midf F3: use the FULL chain-valid set
        # (_cl_rows, recomputed body+parent) — NOT raw rows with a
        # signature-only check. A valid sig over a tampered body/
        # parent must not yield a trusted _start_row.
        _start_row = None
        for r in _cl_rows:
            if (r.get("transition_type") == "start_tick"
                    and str(r.get("tick_id")) == _tid):
                _start_row = r  # FIRST signed start (immutability
                break           # guard ensures it is also the ONLY one)
        if _start_row is None:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "tick_close", "verdict": "quarantine",
                   "failed": [f"no frozen signed `start_tick` contract "
                              f"for tick_id {_tid!r} — the pre-tick "
                              f"contract is daemon-minted, not printed; "
                              f"open the tick via a start_tick "
                              f"transition before closing it"]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec

    # ── START-TICK CONTRACT (pre-tick→contract migration). The daemon
    # MINTS the signed pre-tick contract: it recomputes the obligation
    # set from the goal (un-forgeable) and signs a `start_tick` row
    # carrying tick_id + the mandatory obligations + micro-contract
    # requirement. This REPLACES rd_tick_brief's printed "MANDATORY"
    # prose as the authority. start_tick does NOT discharge obligations
    # (work has not happened yet) ⇒ it skips evaluate()/discharge.
    if str(p.get("transition_type", "")) == "start_tick":
        st = p.get("close") if isinstance(p.get("close"), dict) else {}
        s_tid = str(st.get("tick_id", "")).strip()
        s_goal = str(p.get("goal", "")).strip()
        if not s_tid or not s_goal:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "start_tick", "verdict": "quarantine",
                   "failed": ["start_tick requires close.tick_id + a "
                              "non-empty goal (the contract inputs)"]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        # IMMUTABLE START (final re-review core-fix, bs7ykne6m): exactly
        # ONE chain-valid signed start_tick per tick_id. A duplicate
        # start_tick would let a corrupt agent mint a WEAKER frozen
        # contract over a strong one, then close against it. Reject any
        # start_tick whose tick_id already has a signed start row.
        from ztare.gates._daemon_sig import verify as _vs0
        if any(r.get("transition_type") == "start_tick"
               and str(r.get("tick_id")) == s_tid
               and _vs0(str(r.get("official_state_hash", "")),
                        r.get("daemon_sig"))
               for r in _ledger_rows_raw()):
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "start_tick", "verdict": "quarantine",
                   "failed": [f"start_tick is IMMUTABLE per tick_id: a "
                              f"chain-valid signed start contract for "
                              f"{s_tid!r} already exists — cannot mint a "
                              f"second (would allow strong→weak contract "
                              f"replacement before close)"]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        # GP-238 parts 1-2: STRUCTURAL-ANCHOR forcing rule (NS basin
        # HARD RULE generalized into the generic contract). Every
        # start_tick must NAME which residual_target it addresses; the
        # daemon registry-membership-checks it. MECE: residual_target
        # is a SEPARATE axis from contract_scope (micro/meso/macro) —
        # the WHAT-open-atom axis, not the horizon axis. Unregistered
        # ⇒ require a structured new_target_justification + flag for
        # audit (the Rung-2 fingerprint auto-check was LOO-falsified;
        # naming + registry-membership is the shipped forcing core).
        s_target = str(st.get("residual_target", "")).strip()
        s_substrate = str(st.get("substrate", "")).strip()
        # MECE tick_class axis (genesis/non-research answer): a tick
        # must POSITIVELY declare its kind. research (default) ⇒ must
        # name a registry-checked residual_target. bootstrap/infra/
        # meta/self_test ⇒ EXEMPT from residual_target but recorded as
        # carrying NO research authority (auditable: declaring infra to
        # dodge a research obligation is a distinct misdeclaration, not
        # a silent bypass — same typed-signal principle as elsewhere).
        # This is how the genesis tick / membrane self-tests pass
        # WITHOUT a hole: they declare bootstrap/self_test, not
        # absence; a genesis RESEARCH tick still names its first atom
        # (registry-empty ⇒ recorded unregistered, allowed).
        _NONRESEARCH = {"bootstrap", "infra", "meta", "self_test"}
        s_class = (str(st.get("tick_class", "research"))
                   .strip().lower() or "research")
        _rt_unreg = False
        _rt_canon = s_target
        if s_class in _NONRESEARCH:
            # exempt; no residual_target required, no research authority.
            _rt_canon = ""
            _rt_unreg = False
        elif not s_target or not s_substrate:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "start_tick", "verdict": "quarantine",
                   "failed": [f"start_tick tick_class={s_class!r} "
                              f"(research) must NAME close.substrate + "
                              f"close.residual_target (GP-238 forcing "
                              f"rule). A non-research tick must instead "
                              f"declare close.tick_class ∈ "
                              f"{sorted(_NONRESEARCH)} — absence is "
                              f"refused, declaration is auditable."]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        if s_class not in _NONRESEARCH:
            try:
                import yaml as _yaml
                _reg = _yaml.safe_load(
                    (REPO_ROOT / "org" / "structural_anchors"
                     / "registry.yaml").read_text(encoding="utf-8")) or {}
            except Exception:
                _reg = {}
            _sub = (_reg.get(s_substrate)
                    if isinstance(_reg, dict) else None)
            if isinstance(_sub, dict):
                _norm = lambda x: re.sub(r"[^a-z0-9]+", "",
                                         str(x).lower())
                _hit = None
                for _t in (_sub.get("targets") or []):
                    _names = ([_t.get("id")]
                              + list(_t.get("aliases") or []))
                    if _norm(s_target) in {
                            _norm(n) for n in _names if n}:
                        _hit = _t.get("id")
                        break
                if _hit:
                    _rt_canon = _hit
                else:
                    _rt_unreg = True
                    if not str(st.get("new_target_justification",
                                      "")).strip():
                        rec = {"ts": _now(), "proposal_id": pid,
                               "transition_type": "start_tick",
                               "verdict": "quarantine",
                               "failed": [
                                  f"residual_target {s_target!r} is "
                                  f"NOT in the {s_substrate} "
                                  f"structural-anchor registry — a "
                                  f"'reduction to a new open thing' "
                                  f"REQUIRES "
                                  f"close.new_target_justification "
                                  f"(structured: why this is genuinely "
                                  f"a new irreducible atom, not a "
                                  f"re-vocabularization). Unjustified "
                                  f"⇒ amnesia, refused."]}
                        (QUARANTINE
                         / f"{proposal_path.stem}.quarantine.json"
                         ).write_text(json.dumps(rec, indent=2))
                        proposal_path.unlink(missing_ok=True)
                        return rec
            else:
                # substrate not in registry ⇒ degrade to named +
                # recorded (flagged) — generic, no NS coupling.
                _rt_unreg = True
        from ztare.surfacing.pre_tick_obligation_compiler import (
            start_tick as _compile, merge_signals as _ms)
        _sig_in = _ms(p.get("declared_signals"),
                      f"{p.get('transition_text','')} {s_goal}")
        _c = _compile(s_goal, str(st.get("transition_type", "")), _sig_in)
        # F3 (Meta-Darwin bwdcoww2y): freeze the FORECAST IDENTITY into
        # the signed start row so a close cannot bind a different /
        # weaker / unrelated forecast contract than the tick opened
        # on. Optional-but-enforced-when-present: if the start
        # proposal declares forecast_contract_id and the file exists,
        # freeze its sha256 + question_hash + consumes_surfaced +
        # layer + created_by; else mark forecast_identity_frozen=False
        # (pre-schema ticks are NOT false-FAILed — the gates only
        # compare when frozen). The agent cannot forge these: the
        # daemon hashes the on-disk contract itself.
        _fc_id = str(st.get("forecast_contract_id", "") or "")
        _fc = {"forecast_contract_id": _fc_id or None,
               "forecast_contract_sha256": None,
               # GP-241 #54: persist the EXACT carried contract bytes
               # into the daemon-SIGNED start row so close-validation
               # can RECOVER them from the chain instead of re-reading
               # the agent-writable (and git-clean-fragile) working-tree
               # file. #52 fixed the FREEZE side of this trust-boundary;
               # the close side still re-read disk ⇒ a `git clean`
               # between start and close made the tick permanently
               # uncloseable. Strictly stronger than the disk re-read
               # (daemon-signed, tamper-evident) — identity already
               # bound by the sha; this just makes the frozen artifact
               # durable. None for legacy/co-located starts.
               "forecast_contract_b64": None,
               "forecast_question_hash": None,
               "forecast_consumes_surfaced": None,
               "forecast_layer": None,
               "forecast_created_by": None,
               "forecast_identity_frozen": False}
        if _fc_id:
            try:
                # GP-241 #52: PREFER the contract bytes carried in the
                # proposal (start_tick.py emits forecast_contract_b64).
                # The proposal arrived via the daemon-OWNED inbox whose
                # exact content the daemon already hashes into the
                # chain, so this is no weaker than re-reading a file —
                # and it eliminates the cross-trust-boundary path bug
                # (daemon REPO_ROOT=/srv/ztare_gate never saw the
                # agent-authored contract in ~ztare ⇒ frozen=False for
                # the entire session). Freezing binds IDENTITY not
                # trust: a forged proposal only freezes the forged
                # thing, exactly as a forged file did. File read kept
                # as a backward-compat fallback for legacy/co-located
                # callers that do not carry the bytes.
                _raw = None
                _b64v = st.get("forecast_contract_b64")
                if _b64v:
                    import base64 as _b64m
                    _raw = _b64m.b64decode(_b64v)
                else:
                    _fcp = (REPO_ROOT / "analytics/public/forecast_pool"
                            / "contracts" / f"{_fc_id}.json")
                    if _fcp.is_file():
                        _raw = _fcp.read_bytes()
                if _raw is not None:
                    _fj = json.loads(_raw.decode("utf-8", "ignore"))
                    _q = str(_fj.get("question", "")
                             or _fj.get("contract_question", "") or "")
                    import base64 as _b64s
                    _fc.update({
                        "forecast_contract_sha256":
                            hashlib.sha256(_raw).hexdigest(),
                        "forecast_contract_b64":
                            _b64s.b64encode(_raw).decode("ascii"),
                        "forecast_question_hash":
                            hashlib.sha256(
                                _q.strip().encode()).hexdigest()[:16],
                        "forecast_consumes_surfaced":
                            _fj.get("consumes_surfaced"),
                        "forecast_layer": str(_fj.get("layer", "")
                                              or ""),
                        "forecast_created_by":
                            str(_fj.get("created_by", "")
                                or _fj.get("owner", "") or ""),
                        "forecast_identity_frozen": True})
            except Exception:
                _fc["forecast_identity_frozen"] = False
        # SM2 / cold review b5upqb5kz F2: FORCE it (was: optional ⇒
        # start_tick.py was laundering, not forcing). A research tick
        # MUST open with a valid, daemon-hashable forecast contract;
        # else the close-side F3 forecast binding is unenforceable.
        # Non-research ticks (genesis/admin) are exempt.
        if (s_class not in _NONRESEARCH) and not _fc[
                "forecast_identity_frozen"]:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "start_tick",
                   "verdict": "quarantine",
                   "failed": [
                       f"research start_tick MUST declare a valid "
                       f"forecast_contract_id whose contract file "
                       f"the daemon can hash (got "
                       f"{_fc_id or 'NONE'!r}; frozen="
                       f"{_fc['forecast_identity_frozen']}). Open via "
                       f"start_tick.py --forecast-contract-id <id>. "
                       f"This is the SM2 forcing: no frozen forecast "
                       f"identity ⇒ no research tick."]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        parent = _parent_hash()
        srow = {
            "ts": _now(), "proposal_id": pid,
            "proposal_body_sha256": body_sha,
            "transition_type": "start_tick",
            "tick_id": s_tid, "goal": s_goal,
            "contract_id": (_c.contract_id if _c else None),
            "mandatory_obligations": (
                [o["item_id"] for o in _c.mandatory_obligations]
                if _c else []),
            "mandatory_obligation_discharge": (
                {o["item_id"]: o.get("discharge", {"mode": "judge"})
                 for o in _c.mandatory_obligations}
                if _c else {}),
            # FULL frozen contract snapshot so the close can be
            # validated against the EXACT contract minted at open
            # (final-review core-fix: presence-only binding was a
            # semantic fail-open — open strong, close weak).
            "start_transition_type": str(st.get("transition_type", "")),
            "start_declared_signals": {k: True for k, v in
                                       (_sig_in or {}).items() if v},
            # GP-238 parts 1-2: structural anchor frozen into the
            # signed contract (close inherits it via the frozen-start
            # binding). tick_class is the MECE genesis/non-research
            # axis; residual_target_unregistered flags audit need.
            "tick_class": s_class,
            "substrate": s_substrate,
            "residual_target": _rt_canon,
            "residual_target_raw": s_target,
            "residual_target_unregistered": bool(_rt_unreg),
            "research_authority": (s_class not in _NONRESEARCH),
            "contract_scope_required": "micro",
            **_fc,
            "verifier_id": "commit_membrane_daemon",
            "gate_version": GATE_VERSION,
            "parent_state_hash": parent,
            "membrane_stamp": f"START:{s_tid}",
            "verdict": "pass",
        }
        _blob = json.dumps(srow, sort_keys=True)
        srow["official_state_hash"] = hashlib.sha256(
            (parent + _blob).encode()).hexdigest()[:32]
        from ztare.gates._daemon_sig import sign as _sgn
        srow["daemon_sig"] = _sgn(srow["official_state_hash"])
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(srow) + "\n")
        proposal_path.unlink(missing_ok=True)
        return {"verdict": "pass", "proposal_id": pid,
                "transition_type": "start_tick", "tick_id": s_tid,
                "official_state_hash": srow["official_state_hash"],
                "mandatory_obligations": srow["mandatory_obligations"]}

    # R2 (Meta-Darwin bwdcoww2y): manifest provenance. The daemon
    # otherwise TRUSTS an agent-written pretick/posttick manifest. A
    # `manifest_receipt` transition makes it tamper-evident: the
    # daemon itself hashes the on-disk manifest, requires status==
    # COMPLETE, and SIGNS {tick_id, manifest_kind, manifest_sha256}
    # into the hash-chained ledger. At close the daemon recomputes
    # the file hash and requires a chain-valid signed receipt that
    # matches — so post-receipt tampering or a forged COMPLETE flag
    # fails closed. The agent cannot forge daemon_sig.
    if str(p.get("transition_type", "")) == "manifest_receipt":
        st = p.get("close") if isinstance(p.get("close"), dict) else {}
        m_tid = str(st.get("tick_id", "")).strip()
        m_kind = str(st.get("manifest_kind", "")).strip()
        _fail = None
        if m_kind not in ("pretick", "posttick") or not m_tid:
            _fail = ("manifest_receipt requires close.tick_id + "
                     "manifest_kind in {pretick,posttick}")
        else:
            # cold review b5upqb5kz F1 (remote transport): the receipt
            # CARRIES the manifest bytes (close.manifest_b64). The
            # daemon decodes them, validates, writes them to DAEMON-
            # OWNED storage, and hashes the RECEIVED bytes — so a
            # laptop→VPS remote-enforce run no longer depends on the
            # manifest file existing on the VPS. Co-located fallback:
            # if no bytes are carried, read the local path (legacy).
            _mb = None
            _b64 = st.get("manifest_b64")
            if isinstance(_b64, str) and _b64.strip():
                try:
                    import base64 as _bb
                    _mb = _bb.b64decode(_b64)
                except Exception:
                    _fail = "manifest_b64 not decodable"
            if _mb is None and _fail is None:
                _lp = (REPO_ROOT / "analytics" / "public" / m_kind
                       / m_tid / f"{m_kind}_manifest.json")
                if _lp.is_file():
                    _mb = _lp.read_bytes()
                else:
                    _fail = (f"manifest_receipt carried no "
                             f"manifest_b64 AND no local "
                             f"{m_kind}_manifest.json for {m_tid!r} "
                             f"(remote-enforce MUST carry bytes)")
            if _mb is not None and _fail is None:
                try:
                    _mj = json.loads(_mb.decode("utf-8", "ignore"))
                    if str(_mj.get("status")) != "COMPLETE":
                        _fail = (f"{m_kind}_manifest status="
                                 f"{_mj.get('status')!r} (not "
                                 f"COMPLETE) — no receipt for an "
                                 f"incomplete manifest")
                    elif str(_mj.get("tick_id")) != m_tid:
                        _fail = (f"{m_kind}_manifest tick_id != "
                                 f"{m_tid!r}")
                    else:
                        # GP-241 #56b — LATEST-receipt-wins (supersede),
                        # replacing the old C1 first-receipt-wins. RCA:
                        # C1 made a scientifically-COMPLETE tick whose
                        # FIRST pretick used a paraphrased goal
                        # permanently uncloseable (the corrected-goal
                        # manifest could never get a receipt; no re-roll
                        # possible). C1's anti-churn property is
                        # REDUNDANT with the close-time binds: the close
                        # independently enforces pretick/posttick
                        # manifest.goal == the frozen+SIGNED start goal,
                        # substrate == frozen substrate, status ==
                        # COMPLETE, AND that a chain-valid receipt
                        # matches the CURRENT manifest sha (R2). A
                        # churned/wrong-goal manifest therefore STILL
                        # fails the close goal/substrate bind regardless
                        # of which receipt is pinned — last-wins changes
                        # nothing an attacker can exploit, it only lets
                        # an honest agent correct a first-run goal
                        # paraphrase on a real tick. Same trust model as
                        # #52/#54: the receipt is tamper-evident
                        # provenance ("a COMPLETE pre/post-tick ran for
                        # this tick"); WHICH content is legitimate is
                        # decided at CLOSE against the frozen signed
                        # start row, not by receipt immutability.
                        _mdir = OFFICIAL / "manifests"
                        _mdir.mkdir(parents=True, exist_ok=True)
                        _mfile = _mdir / f"{m_tid}.{m_kind}.json"
                        # idempotent if identical; else supersede
                        # (pin the latest COMPLETE manifest bytes).
                        _mfile.write_bytes(_mb)
                except Exception as _me:
                    _fail = (f"{m_kind}_manifest unreadable "
                             f"({type(_me).__name__})")
        if _fail:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "manifest_receipt",
                   "verdict": "quarantine", "failed": [_fail]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        parent = _parent_hash()
        mrow = {
            "ts": _now(), "proposal_id": pid,
            "proposal_body_sha256": body_sha,
            "transition_type": "manifest_receipt",
            "tick_id": m_tid, "manifest_kind": m_kind,
            "manifest_sha256": hashlib.sha256(_mb).hexdigest(),
            "verifier_id": "commit_membrane_daemon",
            "gate_version": GATE_VERSION,
            "parent_state_hash": parent,
            "membrane_stamp": f"MANIFEST:{m_kind}:{m_tid}",
            "verdict": "pass",
        }
        _mblob = json.dumps(mrow, sort_keys=True)
        mrow["official_state_hash"] = hashlib.sha256(
            (parent + _mblob).encode()).hexdigest()[:32]
        from ztare.gates._daemon_sig import sign as _sgn
        mrow["daemon_sig"] = _sgn(mrow["official_state_hash"])
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(mrow) + "\n")
        proposal_path.unlink(missing_ok=True)
        return {"verdict": "pass", "proposal_id": pid,
                "transition_type": "manifest_receipt",
                "tick_id": m_tid, "manifest_kind": m_kind,
                "manifest_sha256": mrow["manifest_sha256"],
                "official_state_hash": mrow["official_state_hash"]}

    # R5''' provenance (cold review bq4z7midf): the target-statement
    # registry was an agent-WRITABLE json file ⇒ the agent could add
    # its own hash and self-authorize a "Clay closure". A
    # `target_register` transition moves the trust into daemon-signed
    # hash-chained official state: the daemon signs {statement_sha256,
    # label} and the closure check requires a CHAIN-VALID signed
    # target_register row — the agent cannot forge daemon_sig.
    # HONEST RESIDUAL (NOT claimed solved): operator-vs-agent gating
    # of WHO may submit a target_register is the SAME R2-class
    # provenance residual as admin_retire — it is operator-attested
    # (env ZTARE_OPERATOR_TARGET=1 + the proposal's i_am_operator
    # flag), loud, and ledgered, NOT cryptographically operator-only
    # (that needs keys outside the agent boundary; deploy layer).
    if str(p.get("transition_type", "")) == "target_register":
        from ztare.gates._daemon_sig import (
            operator_anchor_provisioned, operator_verify)
        st = p.get("close") if isinstance(p.get("close"), dict) else {}
        # Self-MD round-3 (B): prefer close.statement_text and compute
        # the hash HERE via the SAME canonical_statement the Lean gate
        # uses for proven theorems — so operator and prover normalize
        # identically (a hand-hashed value risks SM3 false-FAILing an
        # honest faithful proof on a normalization divergence).
        _stext = str(st.get("statement_text", "") or "")
        _tsha = str(st.get("statement_sha256", "")).strip().lower()
        if _stext.strip():
            try:
                from ztare.gates.lean_proof_gate import (
                    canonical_statement as _canon)
                _tsha = hashlib.sha256(
                    _canon(_stext).encode("utf-8")).hexdigest()
            except Exception:
                _tsha = ""
        _tlabel = str(st.get("label", "")).strip()
        # C2 (forward-spec): operator-IDENTITY boundary. The env-flag
        # "attestation" an agent runtime could carry is REPLACED by an
        # ed25519 signature from the pinned operator key (agent- and
        # daemon-signer-unreadable). The operator signs the canonical
        # payload offline:  f"{_tsha}|{label}|{env_hash}"  where
        # env_hash binds the import/extractor environment. Anchor
        # unprovisioned ⇒ BLOCKED (fail-closed), never accept.
        _env_hash = str(st.get("env_hash", "") or "")
        _osig = st.get("operator_sig")
        _payload = f"{_tsha}|{_tlabel}|{_env_hash}"
        _tf = None
        if not _re_hex64(_tsha):
            _tf = ("target_register requires close.statement_text "
                   "(preferred; daemon canonicalizes+hashes it the "
                   "same way the Lean gate hashes proven theorems) "
                   "OR a precomputed 64-hex statement_sha256, + a "
                   "label")
        elif not _tlabel:
            _tf = "target_register requires a non-empty label"
        elif not operator_anchor_provisioned():
            _tf = ("C2 BLOCKED: the pinned operator pubkey anchor is "
                   "not provisioned (deploy/gp241_operator_pubkey.hex "
                   "is the placeholder) — fail-closed, NO target may "
                   "be registered until the operator provisions the "
                   "key. This is intentional (P5: no allow-until-"
                   "provisioned).")
        elif not operator_verify(_payload, _osig):
            _tf = ("C2: target_register requires a valid "
                   "close.operator_sig (ed25519 over "
                   "f'{statement_sha256}|{label}|{env_hash}') by the "
                   "PINNED operator key — the agent runtime cannot "
                   "hold it. An i_am_operator flag / env var is no "
                   "longer accepted (it was forgeable).")
        if _tf:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "target_register",
                   "verdict": "quarantine", "failed": [_tf]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        parent = _parent_hash()
        trow = {
            "ts": _now(), "proposal_id": pid,
            "proposal_body_sha256": body_sha,
            "transition_type": "target_register",
            "statement_sha256": _tsha, "label": _tlabel,
            # C3: persist the canonical statement TEXT + the
            # elaboration env_hash into the signed, chain-valid row so
            # a close can run a Lean-kernel defeq probe against this
            # exact registered text in this exact pinned environment.
            "statement_text": _stext,
            "env_hash": _env_hash,
            "operator_attested": True,
            "verifier_id": "commit_membrane_daemon",
            "gate_version": GATE_VERSION,
            "parent_state_hash": parent,
            "membrane_stamp": f"TARGET:{_tsha[:12]}",
            "verdict": "pass",
        }
        _tblob = json.dumps(trow, sort_keys=True)
        trow["official_state_hash"] = hashlib.sha256(
            (parent + _tblob).encode()).hexdigest()[:32]
        from ztare.gates._daemon_sig import sign as _sgn
        trow["daemon_sig"] = _sgn(trow["official_state_hash"])
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(trow) + "\n")
        proposal_path.unlink(missing_ok=True)
        return {"verdict": "pass", "proposal_id": pid,
                "transition_type": "target_register",
                "statement_sha256": _tsha, "label": _tlabel,
                "official_state_hash": trow["official_state_hash"]}

    # Contract C4: admin_retire under the operator-identity boundary.
    # The ONLY liveness escape hatch for a jammed tick was gated by a
    # forgeable env flag (ZTARE_OPERATOR_RETIRE) + --i-am-operator and
    # bypassed the daemon (local tombstone). C4 makes it a DAEMON-
    # mediated, operator-signed transition: no signature ⇒ no retire.
    # The env-flag path is DELETED in admin_retire_uncloseable_tick.py
    # (a forgeable path that still exists is still the hole). NOTE
    # (stated, not hidden): the signature is unforgeable GIVEN the OS
    # topology — it is only "taken away from the agent" where the
    # agent process cannot read the operator key and has no sudo path.
    # That precondition is C4's first-class not-the-builder acceptance
    # criterion (the deploy triad check), not asserted here.
    if str(p.get("transition_type", "")) == "tick_retire":
        from ztare.gates._daemon_sig import (
            operator_anchor_provisioned, operator_verify)
        st = p.get("close") if isinstance(p.get("close"), dict) else {}
        _ro = str(st.get("owner", "")).strip()
        _rt = str(st.get("tick_row", "")).strip()
        _rr = str(st.get("reason", "")).strip()
        _rts = str(st.get("ts", "")).strip()
        _rsig = st.get("operator_sig")
        _R_REASONS = {"legacy_raw_propose_no_forecast_contract",
                      "legacy_audit_finding_no_forecast_contract",
                      "pre_lifecycle_bypass_debt"}
        _rpayload = f"{_ro}|{_rt}|{_rr}|{_rts}"
        _rf = None
        # ts freshness (replay kill): ISO8601, within ±1h of now.
        _fresh = False
        try:
            import datetime as _dt
            _t = _dt.datetime.fromisoformat(_rts.replace("Z", "+00:00"))
            if _t.tzinfo is None:
                _t = _t.replace(tzinfo=_dt.timezone.utc)
            _age = abs((_dt.datetime.now(_dt.timezone.utc)
                        - _t).total_seconds())
            _fresh = _age <= 3600
        except Exception:
            _fresh = False
        if not (_ro and _rt):
            _rf = "tick_retire requires close.owner + close.tick_row"
        elif _rr not in _R_REASONS:
            _rf = (f"tick_retire reason {_rr!r} not in "
                   f"{sorted(_R_REASONS)}")
        elif not _rts or not _fresh:
            _rf = ("tick_retire requires a fresh ISO8601 close.ts "
                   "(±1h; replay-kill) — stale/missing rejected")
        elif not operator_anchor_provisioned():
            _rf = ("C4 BLOCKED: operator pubkey anchor unprovisioned "
                   "— NO retire until the operator provisions the "
                   "key. Intended fail-closed: a wedged loop is safe; "
                   "a forgeable liveness hatch is not (P5).")
        elif not operator_verify(_rpayload, _rsig):
            _rf = ("C4: tick_retire requires a valid close."
                   "operator_sig (ed25519 over "
                   "f'{owner}|{tick_row}|{reason}|{ts}') by the "
                   "PINNED operator key — the agent runtime cannot "
                   "hold it. The env-flag/i_am_operator path is "
                   "DELETED, not deprecated.")
        if _rf:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "tick_retire",
                   "verdict": "quarantine", "failed": [_rf]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        parent = _parent_hash()
        rrow = {
            "ts": _now(), "proposal_id": pid,
            "proposal_body_sha256": body_sha,
            "transition_type": "tick_retire",
            "owner": _ro, "tick_row": _rt, "reason": _rr,
            "retire_ts": _rts,
            "counts_as_tick_close": False,
            "rd_lifecycle_valid": False,
            "not_creditable_for": ["micro_forecast", "GP-230",
                                   "GP-233", "surfaced_consumption"],
            "operator_attested": True,
            "verifier_id": "commit_membrane_daemon",
            "gate_version": GATE_VERSION,
            "parent_state_hash": parent,
            "membrane_stamp": f"RETIRE:{_rt[:24]}",
            "verdict": "pass",
        }
        _rblob = json.dumps(rrow, sort_keys=True)
        rrow["official_state_hash"] = hashlib.sha256(
            (parent + _rblob).encode()).hexdigest()[:32]
        from ztare.gates._daemon_sig import sign as _sgn
        rrow["daemon_sig"] = _sgn(rrow["official_state_hash"])
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rrow) + "\n")
        proposal_path.unlink(missing_ok=True)
        return {"verdict": "pass", "proposal_id": pid,
                "transition_type": "tick_retire",
                "owner": _ro, "tick_row": _rt, "reason": _rr,
                "official_state_hash": rrow["official_state_hash"]}

    # cold round-3 blocker #2: pass the TYPED transition_type so the
    # relapse-guard fail-close (missing residual manifest) triggers on
    # a typed closure/tick_close/forecast_resolution, not only on
    # lexical terminus prose (paraphrase-proof, matches the typed-
    # signal principle used elsewhere in this apparatus).
    _eval_substrate = ""
    if is_close and _start_row is not None:
        _eval_substrate = str(_start_row.get("substrate", "") or "")
    if not _eval_substrate and isinstance(close, dict):
        _eval_substrate = str(close.get("substrate", "") or "")
    if not _eval_substrate and isinstance(declared, dict):
        _eval_substrate = str(declared.get("substrate", "")
                              or declared.get("substrate_slug", "") or "")
    v = evaluate(text, declared, proposal_id=pid,
                 transition_type=str(p.get("transition_type", "")),
                 substrate=_eval_substrate)

    # GP-241 obligation-contract enforcement (cold GPT-5.5 design):
    # "no start-tick contract ⇒ no official close." The daemon
    # RECOMPUTES the contract from the goal (un-forgeable — the agent
    # cannot submit a weaker contract) and requires every mandatory
    # obligation discharged by a witness OR a verifiable why_not.
    oblig_fail: list[str] = []
    goal = str(p.get("goal", "")).strip()
    from ztare.surfacing.pre_tick_obligation_compiler import (
        start_tick, validate_tick_contract, merge_signals)
    _tt = str(p.get("transition_type", ""))
    # sev-5 fix: do NOT trust agent-declared signals alone. The
    # verifier DERIVES signals from the transition text + goal and
    # OR-merges — a declaration may ADD an obligation, never suppress
    # one the text plainly implies (declared-signal underreporting).
    _ds = merge_signals(p.get("declared_signals"),
                        f"{text} {goal}")
    # FINAL-REVIEW CORE-FIX (bq8ria96j): a tick_close must discharge
    # the EXACT contract frozen at open, NOT a contract recomputed
    # from the close proposal's own (possibly weaker) goal/signals.
    # Bind to the signed _start_row: validate the close's witnesses/
    # why_not against the START's goal + transition_type + signals,
    # and require EVERY frozen mandatory obligation discharged.
    if is_close and _start_row is not None:
        # cold review b1djdevru (B): the close's contract_id MUST be
        # the one frozen at start_tick — else a close can bind a
        # foreign contract to a tick's frozen obligations.
        _sc = str(_start_row.get("contract_id", "") or "")
        if _sc and str(close.get("contract_id", "")) != _sc:
            oblig_fail.append(
                f"close.contract_id {close.get('contract_id')!r} != "
                f"frozen start_tick contract_id {_sc!r} "
                f"(foreign-contract binding rejected)")
        # END-TO-END pre-tick enforcement (operator 2026-05-18; trust
        # root = operator inspection of the manifest, not agent self-
        # attestation). The DAEMON is the only real authority (H7;
        # tick_close.py H1-H6 are advisory under GP-241). So the
        # pre-tick is enforced HERE or nowhere. A COMPLETE pretick
        # manifest MUST exist for this tick_id AND be mutually bound to
        # the FROZEN signed start row (tick_id + contract_id) — same
        # un-forgeable binding as the b1djdevru contract check above,
        # which closes the presence≠this-tick gap. Absent/INCOMPLETE/
        # mismatched ⇒ oblig_fail ⇒ the existing path QUARANTINES
        # (fail-closed). Any read error is fail-closed (a HARD entry),
        # never a daemon crash.
        _tid = str(close.get("tick_id", "") or "")
        # Shared by BOTH the pre- and post-tick gates (hoisted so the
        # post-gate never NameErrors when the pretick manifest is
        # absent). substrate/goal are frozen+signed in _start_row.
        _fg = str(_start_row.get("goal", "") or "").strip()
        _fs_sub = str(_start_row.get("substrate", "") or "")
        # GP-241 #56: the frozen FORECAST IDENTITY slug. start_tick
        # freezes contract_id := the daemon _compile(goal,transition)
        # cid, but the forecast contract (init-contract / resolve /
        # outcome file / gp230 / H4) is keyed by the human forecast
        # slug. pretick/posttick_runner bind to the forecast slug
        # ("the contract this tick consumes"); their manifest.cid is
        # therefore compile(slug) ≠ the compile(goal) frozen cid — a
        # divergence-by-construction that made EVERY clean membrane-
        # FIRST forecast tick uncloseable (a scientifically-complete
        # tick could not pass the cid bind). The forecast slug IS
        # frozen+signed into _start_row (forecast_contract_id, bound
        # un-forgeably via the #52/#54 sha) and the manifest is daemon-
        # receipt-registered + R2 tamper-evident, so accepting a
        # manifest whose forecast_contract_id == this frozen slug is
        # the SAME anti-bypass property (pre/post-tick provably bound
        # to the forecast identity THIS tick froze), just keyed on the
        # forecast identity instead of the divergent compiler cid. No
        # weakening: a forged/foreign manifest still fails (slug is
        # signed; manifest is receipt-registered).
        _ffslug = str(_start_row.get("forecast_contract_id", "") or "")

        # GENERIC string normalizer (NOT substrate-aware). The daemon
        # is the substrate-AGNOSTIC commit membrane; it must not know
        # what "NS" is. The substrate-swap bypass is closed purely by
        # EXACT binding of the manifest substrate to the FROZEN SIGNED
        # start-row substrate — once that holds, the agent cannot run
        # the pre/post-tick under a different substrate than the tick
        # froze, so substrate-specific required steps cannot be
        # skipped. Which steps a substrate requires is decided in the
        # runner (substrate-aware by design), never here.
        def _subnorm(x: str) -> str:
            return "".join(ch for ch in str(x).strip().lower()
                           if ch.isalnum() or ch == "_")
        try:
            _pm = _daemon_manifest(_tid, "pretick")
            if not _pm.is_file():
                oblig_fail.append(
                    f"pretick_manifest MISSING for tick {_tid!r} "
                    f"(analytics/public/pretick/{_tid}/) — the "
                    f"pre-tick (amnesia/menu/pattern/forecast/GP-233) "
                    f"was not RUN; run pretick_runner.py first "
                    f"(fail-closed: no pre-tick ⇒ no close)")
            else:
                _mj = json.loads(_pm.read_text(encoding="utf-8"))
                if str(_mj.get("status")) != "COMPLETE":
                    oblig_fail.append(
                        f"pretick_manifest status="
                        f"{_mj.get('status')!r} (not COMPLETE) — "
                        f"failed pre-tick steps: "
                        f"{[s.get('step') for s in (_mj.get('steps') or []) if not s.get('ok')]}")
                if str(_mj.get("tick_id")) != _tid:
                    oblig_fail.append(
                        f"pretick_manifest tick_id "
                        f"{_mj.get('tick_id')!r} != close tick_id "
                        f"{_tid!r} (foreign-manifest binding rejected)")
                _mc = str(_mj.get("contract_id", "") or "")
                _mfslug = str(_mj.get("forecast_contract_id", "")
                              or "")
                # #56 cross-walk: bind OK if the compiler cid matches
                # OR the manifest's forecast_contract_id == the frozen
                # forecast slug (same anti-bypass property; see _ffslug
                # note). Only the cid-mismatch arm gets the cross-walk;
                # the no-contract-id arm still fails closed.
                if _sc and _mc and _mc != _sc and not (
                        _ffslug and _mfslug
                        and _mfslug == _ffslug):
                    oblig_fail.append(
                        f"pretick_manifest contract_id {_mc!r} != "
                        f"frozen start_tick contract_id {_sc!r} "
                        f"AND forecast_contract_id {_mfslug!r} != "
                        f"frozen forecast slug {_ffslug!r} "
                        f"(presence≠this-tick bypass blocked)")
                elif _sc and not _mc and not (
                        _ffslug and _mfslug
                        and _mfslug == _ffslug):
                    oblig_fail.append(
                        f"pretick_manifest carries NO contract_id "
                        f"and no matching forecast slug — cannot "
                        f"mutually-bind to the frozen tick "
                        f"(unbound pre-tick rejected)")
                # GOAL BINDING: the amnesia/menu/pattern/graph steps
                # key on --goal free-text. Without this, a COMPLETE
                # manifest could be produced by running the pre-tick
                # tools on THROWAWAY goal text, then closing the real
                # contract ("tools ran" decoupled from "the pre-tick
                # THIS tick needed"). The start_row goal is frozen +
                # signed at start_tick, so requiring exact equality
                # forces the pre-tick to have been executed on this
                # tick's actual goal.
                _mg = str(_mj.get("goal", "") or "").strip()
                if _fg and _mg != _fg:
                    oblig_fail.append(
                        f"pretick_manifest goal != frozen start_tick "
                        f"goal — the pre-tick tools were run on "
                        f"different goal text than this tick froze "
                        f"(throwaway-pretick bypass blocked); "
                        f"manifest={_mg[:80]!r} frozen={_fg[:80]!r}")
                # SUBSTRATE BINDING (cold re-review b18zbkhdw): the
                # compiler cid EXCLUDES substrate, so without this an
                # agent could run the pre-tick under a different
                # substrate (skipping substrate-specific required
                # steps) yet close the real tick. EXACT binding to the
                # frozen+signed start-row substrate closes it,
                # substrate-AGNOSTICally — the daemon never inspects
                # which substrate it is; the runner owns that.
                _ms_sub = str(_mj.get("substrate", "") or "")
                if _fs_sub and _subnorm(_ms_sub) != _subnorm(_fs_sub):
                    oblig_fail.append(
                        f"pretick_manifest substrate {_ms_sub!r} != "
                        f"frozen start_tick substrate {_fs_sub!r} "
                        f"(substrate-swap bypass blocked)")
                # R2: the manifest must be daemon-receipt-registered
                # (tamper-evident). Recompute the file hash NOW and
                # require a chain-valid signed manifest_receipt that
                # matches — a forged COMPLETE flag or post-receipt
                # edit fails closed (the agent cannot forge the sig).
                _psha = hashlib.sha256(_pm.read_bytes()).hexdigest()
                if not _manifest_receipt_ok(_tid, "pretick", _psha):
                    oblig_fail.append(
                        "pretick_manifest has NO chain-valid signed "
                        "manifest_receipt matching its current hash "
                        "(unregistered or tampered after receipt) — "
                        "submit a `manifest_receipt` transition; the "
                        "daemon will not trust an agent-written "
                        "manifest on its COMPLETE flag alone (R2)")
        except Exception as _pe:
            oblig_fail.append(
                f"pretick_manifest unreadable for {_tid!r} "
                f"({type(_pe).__name__}) — fail-closed (no verifiable "
                f"pre-tick ⇒ no close)")
        # SYMMETRIC POST-TICK GATE (operator: "can we do the same for
        # the post checks"). Mirrors the pre-tick gate exactly: the
        # POST-tick MECE legs must have been EXECUTED for THIS tick.
        # posttick_runner writes contract_id = the SAME compiler cid,
        # so the same un-forgeable tick_id + cid + goal + substrate
        # binding applies. Absent/INCOMPLETE/foreign ⇒ oblig_fail ⇒
        # quarantine (fail-closed). Any read error is fail-closed.
        try:
            _qm = _daemon_manifest(_tid, "posttick")
            if not _qm.is_file():
                oblig_fail.append(
                    f"posttick_manifest MISSING for tick {_tid!r} "
                    f"(analytics/public/posttick/{_tid}/) — the "
                    f"POST-tick MECE legs (post_tick_check / micro-"
                    f"resolved / pre<->post bind) were not RUN; run "
                    f"posttick_runner.py before close (fail-closed)")
            else:
                _qj = json.loads(_qm.read_text(encoding="utf-8"))
                if str(_qj.get("status")) != "COMPLETE":
                    oblig_fail.append(
                        f"posttick_manifest status="
                        f"{_qj.get('status')!r} (not COMPLETE) — "
                        f"failed hard legs: "
                        f"{[s.get('step') for s in (_qj.get('steps') or []) if s.get('hard') and not s.get('ok')]}")
                if str(_qj.get("tick_id")) != _tid:
                    oblig_fail.append(
                        f"posttick_manifest tick_id "
                        f"{_qj.get('tick_id')!r} != close tick_id "
                        f"{_tid!r} (foreign-manifest rejected)")
                _qc = str(_qj.get("contract_id", "") or "")
                _qfslug = str(_qj.get("forecast_contract_id", "")
                              or "")
                if _sc and _qc and _qc != _sc and not (
                        _ffslug and _qfslug
                        and _qfslug == _ffslug):
                    oblig_fail.append(
                        f"posttick_manifest contract_id {_qc!r} != "
                        f"frozen start_tick cid {_sc!r} AND "
                        f"forecast_contract_id {_qfslug!r} != frozen "
                        f"forecast slug {_ffslug!r} "
                        f"(presence≠this-tick bypass blocked)")
                elif _sc and not _qc and not (
                        _ffslug and _qfslug
                        and _qfslug == _ffslug):
                    oblig_fail.append(
                        "posttick_manifest carries NO contract_id and "
                        "no matching forecast slug — cannot mutually-"
                        "bind (unbound post rejected)")
                _qg = str(_qj.get("goal", "") or "").strip()
                if _fg and _qg != _fg:
                    oblig_fail.append(
                        f"posttick_manifest goal != frozen start goal "
                        f"(throwaway-posttick bypass blocked); "
                        f"manifest={_qg[:60]!r} frozen={_fg[:60]!r}")
                _qs = str(_qj.get("substrate", "") or "")
                if _fs_sub and _subnorm(_qs) != _subnorm(_fs_sub):
                    oblig_fail.append(
                        f"posttick_manifest substrate {_qs!r} != "
                        f"frozen start substrate {_fs_sub!r} "
                        f"(substrate-swap bypass blocked)")
                # R2 (symmetric): posttick manifest must also be
                # daemon-receipt-registered + hash-matched.
                _qsha = hashlib.sha256(_qm.read_bytes()).hexdigest()
                if not _manifest_receipt_ok(_tid, "posttick", _qsha):
                    oblig_fail.append(
                        "posttick_manifest has NO chain-valid signed "
                        "manifest_receipt matching its current hash "
                        "(unregistered or tampered after receipt) — "
                        "submit a `manifest_receipt` transition (R2)")
        except Exception as _qe:
            oblig_fail.append(
                f"posttick_manifest unreadable for {_tid!r} "
                f"({type(_qe).__name__}) — fail-closed (no verifiable "
                f"post-tick ⇒ no close)")
        # F3 close-side: when the forecast identity was frozen at
        # start, the close MUST bind the SAME forecast contract and
        # the on-disk contract MUST still hash to the frozen sha256
        # (detects swap to a weaker/unrelated contract OR post-start
        # mutation of the contract body). Only enforced when frozen
        # (pre-schema ticks not false-FAILed).
        try:
            # SM2 close-side punisher (cold b5upqb5kz F2): a RESEARCH
            # close whose frozen start row has no frozen forecast
            # identity is refused. New ticks cannot reach this (start-
            # side forcing above); this catches LEGACY pre-forcing
            # start rows so they cannot close as research.
            if (_start_row.get("research_authority") is True
                    and _start_row.get(
                        "forecast_identity_frozen") is not True):
                oblig_fail.append(
                    "research close but the frozen start row has NO "
                    "forecast identity (legacy pre-SM2 start) — "
                    "cannot close as research; re-open via "
                    "start_tick.py --forecast-contract-id (SM2)")
            if _start_row.get("forecast_identity_frozen") is True:
                _ffid = str(_start_row.get(
                    "forecast_contract_id", "") or "")
                _cfid = str(close.get("forecast_contract_id", "")
                            or "")
                if _ffid and _cfid and _cfid != _ffid:
                    oblig_fail.append(
                        f"close forecast_contract_id {_cfid!r} != "
                        f"frozen {_ffid!r} (forecast-swap blocked)")
                elif _ffid and not _cfid:
                    oblig_fail.append(
                        "close carries NO forecast_contract_id but "
                        "the tick froze one (unbound forecast)")
                _fsha = str(_start_row.get(
                    "forecast_contract_sha256", "") or "")
                if _ffid and _fsha:
                    # GP-241 #54: RECOVER the frozen contract from the
                    # daemon-signed start row's carried bytes FIRST.
                    # The start row is tamper-evident (official_state_
                    # hash + daemon_sig), so b64 whose sha == the frozen
                    # sha IS the exact contract minted at open — no
                    # weaker than (in fact stronger than) re-reading the
                    # agent-writable working-tree file, and it survives
                    # a `git clean`/reset that wiped the untracked
                    # contracts/ dir (the actual root cause of the
                    # permanently-uncloseable tick). Disk re-read kept
                    # ONLY as a legacy fallback for pre-#54 start rows
                    # that carry no bytes.
                    _cur = ""
                    _src = ""
                    _fb64 = _start_row.get("forecast_contract_b64")
                    if _fb64:
                        try:
                            import base64 as _b64r
                            _cur = hashlib.sha256(
                                _b64r.b64decode(_fb64)).hexdigest()
                            _src = "chain"
                        except Exception:
                            _cur = ""
                    if not _cur:
                        _fcp = (REPO_ROOT / "analytics/public"
                                / "forecast_pool" / "contracts"
                                / f"{_ffid}.json")
                        _cur = (hashlib.sha256(
                            _fcp.read_bytes()).hexdigest()
                            if _fcp.is_file() else "")
                        _src = "disk-legacy"
                    if _cur != _fsha:
                        oblig_fail.append(
                            f"forecast contract {_ffid!r} body "
                            f"sha256 changed since start "
                            f"(frozen={_fsha[:12]} "
                            f"now={_cur[:12] or 'MISSING'} "
                            f"via {_src or 'none'}) — "
                            f"post-start contract mutation blocked")
        except Exception as _fe:
            oblig_fail.append(
                f"forecast-identity check error "
                f"({type(_fe).__name__}) — fail-closed")
        # F6 (Meta-Darwin bwdcoww2y; SELF-CAUGHT false-FAIL fix): the
        # daemon writes close.f_row_body verbatim into the official
        # F-row. Without this an F-row with valid pre/post manifests
        # but an UNRELATED body materializes. The body MUST name its
        # own provenance — but ONLY with tokens an honest agent-
        # authored F-row legitimately contains: the tick_id (the row
        # IS selected by tick_id) and, when the forecast identity was
        # frozen, the forecast SLUG (tick_close.py H3a already refuses
        # a row that does not reference its contract slug, so this is
        # consistent, not a new false-FAIL). The internal compiler
        # cid is NEVER in agent markdown — requiring it would quarant-
        # ine every honest close (my own Meta-Darwin caught this).
        try:
            _fb = str(close.get("f_row_body", "") or "")
            _need_tokens = [("tick_id", _tid)] if _tid else []
            _ff = str(_start_row.get("forecast_contract_id", "")
                      or "")
            if _start_row.get("forecast_identity_frozen") is True \
                    and _ff:
                _need_tokens.append(("forecast contract id", _ff))
            _missing = [lbl for lbl, tok in _need_tokens
                        if tok and tok not in _fb]
            if _need_tokens and _missing:
                oblig_fail.append(
                    f"F-row body does not name its provenance "
                    f"{_missing} — an unrelated/laundered close body "
                    f"cannot be materialized as the official F-row "
                    f"(F6 semantic bind; honest bodies carry these)")
            # F5-daemon: if the body CLAIMS a formal closure, the
            # posttick lean_faithfulness HARD leg must have passed
            # (the daemon already requires posttick COMPLETE; here it
            # additionally requires that specific leg ok+hard) AND a
            # target_statement_hash must be present (full registry
            # check lands with R5'''/#48). Trigger from the body, not
            # caller honesty.
            _claim_hit = _formal_claim_tripwire(_fb)
            if _claim_hit:
                _lf = None
                try:
                    # cold round-3 F3: daemon-owned copy (remote-
                    # enforce safe), not the repo-local path.
                    _qmp = _daemon_manifest(_tid, "posttick")
                    if _qmp.is_file():
                        _qm2 = json.loads(_qmp.read_text("utf-8"))
                        _lf = next(
                            (s for s in (_qm2.get("steps") or [])
                             if s.get("step") == "lean_faithfulness"),
                            None)
                except Exception:
                    _lf = None
                if not (_lf and _lf.get("ok")
                        and _lf.get("hard") is True):
                    oblig_fail.append(
                        "F-row body claims a formal closure but the "
                        "posttick lean_faithfulness HARD leg did not "
                        "pass (closure-claim ⇒ hard Lean receipt "
                        "required; F5-daemon)")
                # R5''' (Meta-Darwin bwdcoww2y): the claimed
                # target_statement_hash must be a member of the
                # OPERATOR-curated registry — not merely present.
                # Per-tick mechanizable part of "is this the Clay
                # statement"; the residual ("is this registry entry
                # actually the Clay problem") is one-time human
                # curation (correctly irreducible). Registry missing/
                # empty ⇒ a closure claim CANNOT be validated ⇒
                # fail-closed (no registry, no Clay-closure).
                # cold review bq4z7midf: provenance now via CHAIN-VALID
                # daemon-signed `target_register` rows (operator-
                # attested), NOT the agent-writable json (removed from
                # the trust path). Empty ⇒ fail-closed.
                import re as _re
                _m = _re.search(
                    r"target_statement_hash['\"]?\s*[:=]\s*"
                    r"['\"]?([0-9a-fA-F]{64})", _fb)
                _claimed_h = _m.group(1).lower() if _m else ""
                _reg = _registered_targets()
                if not _claimed_h:
                    oblig_fail.append(
                        "F-row body claims a formal closure but "
                        "carries NO target_statement_hash=<hex> "
                        "(must bind the proof to an operator-"
                        "registered target; R5''')")
                elif not _reg:
                    oblig_fail.append(
                        "closure claim present but NO chain-valid "
                        "daemon-signed target_register exists — a "
                        "Clay-closure cannot be validated without an "
                        "operator-registered target (R5''' fail-"
                        "closed)")
                elif _claimed_h not in _reg:
                    oblig_fail.append(
                        f"claimed target_statement_hash "
                        f"{_claimed_h[:12]}… is NOT in any chain-"
                        f"valid daemon-signed target_register — "
                        f"unregistered target (R5''' bypass blocked)")
                # SM3 cite-vs-prove: registered-membership above is
                # HARD (sound: 64-hex set membership over a daemon-
                # signed registry). The PROVEN-intersection check
                # (claimed ∈ posttick.proven_statement_hashes) is
                # DOWNGRADED to an advisory tripwire, NOT a quarantine
                # — applying this project's own P15/P16: a regex parse
                # of a formal language (cold round-3 findings 4/5:
                # `let … := …` mis-parse, comment-marker-in-string
                # collisions, alpha/notation false-FAILs) must not be
                # a HARD gate; it has a next adversarial input by
                # construction. The HARD faithfulness floor remains
                # lean_faithfulness gate_passed (compile + axiom +
                # v33). The sound upgrade is Lean-kernel elaboration
                # (defeq/alpha type identity in a trusted env) —
                # specced, NOT hand-patched mid-loop (P15). Recorded
                # for the reviewer; never fatal.
                else:
                    _proven = []
                    try:
                        _qpath = _daemon_manifest(_tid, "posttick")
                        if _qpath.is_file():
                            _qjj = json.loads(
                                _qpath.read_text("utf-8"))
                            _proven = [
                                str(x).lower() for x in
                                (_qjj.get("proven_statement_hashes")
                                 or [])]
                    except Exception:
                        _proven = []
                    v.notes.append(
                        f"SM3 tripwire (advisory, NOT a gate): "
                        f"claimed target {_claimed_h[:12]}… "
                        f"{'∈' if _claimed_h in _proven else '∉'} "
                        f"regex-parsed proven statement hashes "
                        f"{[p[:8] for p in _proven][:4]} — "
                        f"faithfulness HARD floor is the Lean gate; "
                        f"C3 Lean-kernel identity below supersedes it")
                    # C3 (forward-spec): Lean-kernel defeq of the
                    # PROVEN statement text vs the operator-registered
                    # statement text, in the registered env. PASS ⇒
                    # ok; FAIL ⇒ HARD oblig_fail (sound — kernel
                    # defeq, not regex); BLOCKED ⇒ advisory only
                    # (toolchain unavailable ⇒ route to human, never
                    # silent PASS). The decisive inputs (registered
                    # text in a chain-valid signed row; proven text
                    # the daemon re-derives from the manifest) are NOT
                    # agent-authorable — it passes the discriminator.
                    try:
                        _treg = _registered_target_row(_claimed_h)
                        _reg_txt = str((_treg or {}).get(
                            "statement_text", "") or "")
                        _prov_txt = ""
                        _qp2 = _daemon_manifest(_tid, "posttick")
                        if _qp2.is_file():
                            _qj2 = json.loads(_qp2.read_text("utf-8"))
                            for _s in (_qj2.get("steps") or []):
                                if _s.get("step") != "lean_faithfulness":
                                    continue
                                for _th in ((_s.get("receipt") or {})
                                            .get("theorem_statement_hashes")
                                            or []):
                                    if str(_th.get("statement_sha256",
                                                   "")).lower() \
                                            == _claimed_h:
                                        _prov_txt = str(_th.get(
                                            "statement_text", "") or "")
                                        break
                        if _reg_txt and _prov_txt:
                            from ztare.gates.lean_statement_identity \
                                import statements_defeq
                            _verdict, _detail = statements_defeq(
                                _reg_txt, _prov_txt)
                            if _verdict == "FAIL":
                                oblig_fail.append(
                                    f"C3 Lean-kernel defeq FAIL: the "
                                    f"proven statement is NOT defeq "
                                    f"to the operator-registered "
                                    f"target — {_detail[:200]}")
                            elif _verdict == "BLOCKED":
                                v.notes.append(
                                    f"C3 BLOCKED (advisory, NOT a "
                                    f"gate): {_detail[:160]} — "
                                    f"toolchain unavailable; routed "
                                    f"to human residual, not passed")
                            else:
                                v.notes.append(
                                    "C3 PASS: proven statement is "
                                    "Lean-kernel defeq to the "
                                    "registered target")
                        else:
                            v.notes.append(
                                "C3 not evaluable: missing registered "
                                "or proven statement text (advisory)")
                    except Exception as _c3e:
                        v.notes.append(
                            f"C3 probe error ({type(_c3e).__name__}) "
                            f"— advisory, not fatal")
        except Exception as _se:
            oblig_fail.append(
                f"F-row semantic-bind check error "
                f"({type(_se).__name__}) — fail-closed")
        _cg = str(_start_row.get("goal", ""))
        _ctt = str(_start_row.get("start_transition_type", ""))
        _cds = merge_signals(_start_row.get("start_declared_signals"),
                             _cg)
        ok_o, fails_o = validate_tick_contract(
            _cg, p.get("witnesses") or {}, p.get("why_not") or {},
            _ctt, _cds,
            tick_id=str(close.get("tick_id", "")),
            contract_id=str(close.get("contract_id", "")),
            frozen_obligation_discharge=(
                _start_row.get("mandatory_obligation_discharge") or None))
        if not ok_o:
            # += not = : preserve the contract-id-mismatch entry
            # appended above (cold review b1djdevru B).
            oblig_fail += [f"frozen-start obligation undischarged: {f}"
                           for f in fails_o]
        _frozen = set(_start_row.get("mandatory_obligations") or [])
        _disch = set((p.get("witnesses") or {}).keys()) | set(
            (p.get("why_not") or {}).keys())
        _gap = _frozen - _disch
        if _gap:
            oblig_fail.append(
                f"frozen-start contract not satisfied: obligations "
                f"{sorted(_gap)} minted at start_tick "
                f"{_start_row.get('official_state_hash')} have NO "
                f"witness/why_not in this close (open-strong/close-weak "
                f"bypass blocked)")
        # GP-241 #2: for every frozen mandatory obligation whose
        # submitted witness asks for `judge:auto`, the DAEMON emits a
        # signed judge_request (the agent cannot steer the judge). The
        # close still fails THIS round; once the ztare_judge worker has
        # produced the verdict, an identical re-submitted close
        # resolves via the id-free judge:auto resolver.
        for _it in sorted(_frozen):
            # GP-241 #60 FIX: a frozen obligation may be discharged by a
            # `witnesses[_it]` OR a `why_not[_it]` dict — BOTH require a
            # resolving provenance (validate_tick_contract treats them
            # symmetrically). The old code only sourced `witnesses`, so
            # a why_not discharged with provenance `judge:auto` (e.g.
            # `contradicted_by_goal` on a negative-result tick) NEVER
            # got a judge_request emitted ⇒ permanently judge:auto-
            # pending ⇒ a 2nd judge-bound obligation made the tick
            # unclosable (the recurring multi-obligation wall). Source
            # the discharge from EITHER; the judge adjudicates a why_not
            # exactly as a witness (same _canon_wsha / emit / resolver).
            _w = ((p.get("witnesses") or {}).get(_it)
                  or (p.get("why_not") or {}).get(_it))
            if not (isinstance(_w, dict)
                    and str(_w.get("provenance", "")).strip()
                    == "judge:auto"):
                continue
            # If a chain-valid PASS verdict for THIS exact
            # (tick,contract,item,witness) already exists, the
            # obligation is discharged by the resolver — do NOT emit
            # and do NOT append a pending note (that bug made the
            # close un-closable forever even after the verdict).
            if _already_judged(str(close.get("tick_id", "")), _sc,
                               _it, _canon_wsha(_w)):
                continue
            try:
                _st = _emit_judge_request(
                    tick_id=str(close.get("tick_id", "")),
                    contract_id=_sc, item_id=_it, goal=_cg,
                    stt=_ctt,
                    # MUST be the RAW frozen start_declared_signals
                    # (exactly what the judge_verdict handler feeds
                    # judge_prompt_for) — NOT _cds (merged), else the
                    # recomputed prompt_hash mismatches and the legit
                    # path false-quarantines.
                    declared_signals=(_start_row.get(
                        "start_declared_signals") or {}),
                    witness=_w)
            except Exception as _e:
                _st = f"judge_request emit error {type(_e).__name__}"
            oblig_fail.append(
                f"judge:auto pending for {_it!r} — {_st}; the "
                f"out-of-loop judge will produce the verdict, "
                f"then RE-SUBMIT this exact close to resolve")
        recomputed = None  # frozen path is authoritative for closes
    else:
        recomputed = (start_tick(goal, _tt, _ds)
                      if (goal or _tt or _ds) else None)
        if recomputed and recomputed.mandatory_obligations:
            ok_o, fails_o = validate_tick_contract(
                goal, p.get("witnesses") or {}, p.get("why_not") or {},
                _tt, _ds)
            if not ok_o:
                oblig_fail = [f"obligation undischarged: {f}"
                              for f in fails_o]

    if (not v.official) or oblig_fail:
        rec = {
            "ts": _now(), "proposal_id": pid,
            "agent_runtime": p.get("agent_runtime"),
            "transition_type": p.get("transition_type"),
            "verdict": "quarantine",
            "failed": list(v.failed) + oblig_fail, "notes": v.notes,
            "gate_version": GATE_VERSION,
        }
        (QUARANTINE / f"{proposal_path.stem}.quarantine.json").write_text(
            json.dumps(rec, indent=2))
        proposal_path.unlink(missing_ok=True)
        return rec

    parent = _parent_hash()
    row = {
        "ts": _now(), "proposal_id": pid,
        "proposal_body_sha256": body_sha,
        "agent_runtime": p.get("agent_runtime"),
        "session_id": p.get("session_id"), "turn_id": p.get("turn_id"),
        "transition_type": p.get("transition_type"),
        "transition_text": text, "declared": declared,
        # goal + recomputed contract id stamped for audit AND so the
        # in-loop mutator_briefing forcing-provider can ingest this
        # out-of-loop RD state (legitimate: now deterministic + stamped).
        "goal": goal,
        "tick_contract_id": (recomputed.contract_id if recomputed else None),
        "discharged_obligations": (
            [o["item_id"] for o in recomputed.mandatory_obligations]
            if recomputed else []),
        "verifier_id": "commit_membrane_daemon",
        "gate_version": GATE_VERSION,
        "parent_state_hash": parent,
        "membrane_stamp": v.stamp,
        "verdict": "pass",
    }
    if is_close:
        # The tick is the unit of authority: a closed tick exists IFF a
        # daemon-signed row carries transition_type==tick_close AND
        # close_verified==True (read-side enforces this). The structured
        # close fields are bound INTO the signed/body-hashed row.
        row["close_verified"] = True
        row["tick_id"] = str(close["tick_id"])
        row["close_contract_id"] = str(close["contract_id"])
        row["contract_scope"] = "micro"  # MECE: tick-close ≡ micro
        row["f_row_id"] = str(close["f_row_id"])
        # final-review core-fix: bind the EXACT frozen start snapshot
        # this close discharged (provenance: open↔close are the same
        # contract, not a relabel).
        row["start_official_state_hash"] = str(
            (_start_row or {}).get("official_state_hash", ""))
    blob = json.dumps(row, sort_keys=True)
    row["official_state_hash"] = hashlib.sha256(
        (parent + blob).encode()).hexdigest()[:32]
    # cold round-4 blocker: sign the chain head with the ztare_verify-
    # only ed25519 key. Readers require this signature by the PINNED
    # public key, so a fetched chain from any non-daemon endpoint (a
    # forged self-consistent one) is rejected. Signed AFTER the hash ⇒
    # daemon_sig is NOT part of the hashed blob (chain_valid excludes
    # it). A signing failure MUST be loud (no unsigned official row).
    from ztare.gates._daemon_sig import sign as _sign
    row["daemon_sig"] = _sign(row["official_state_hash"])
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    if is_close:
        # Reverse-H3: the DAEMON writes the official F-row, AFTER
        # validation+sign, into the daemon-owned official store. The
        # repo EXPERIMENT_TRACK_RECORD.md becomes a generated EXPORT of
        # this — an agent-written .md row is not authority. Bound to
        # the signed ledger row by official_state_hash + tick_id.
        frow = {
            "ts": _now(), "tick_id": str(close["tick_id"]),
            "f_row_id": str(close["f_row_id"]),
            "contract_id": str(close["contract_id"]),
            "proposal_id": pid,
            "official_state_hash": row["official_state_hash"],
            "body": str(close["f_row_body"]),
        }
        (OFFICIAL / "F_rows.jsonl").open(
            "a", encoding="utf-8").write(json.dumps(frow) + "\n")
        # GP-241 #61 (operator: "the daemon, once it closes" — NOT the
        # RD agent). On a stamped close the DAEMON itself refreshes a
        # durable, self-contained export bundle of the authoritative
        # record into a stable daemon-owned dir. The operator's
        # deploy/vps_pull.sh then does a THIN fetch of this bundle —
        # the agent never has to remember to snapshot (same
        # information-asymmetry removal as #60). Fail-SAFE: the close
        # is already stamped above; an export error must NEVER unwind
        # it or crash the daemon (best-effort, logged).
        try:
            _exp = OFFICIAL / "export"
            _exp.mkdir(parents=True, exist_ok=True)
            import shutil as _sh
            for _src in ("transitions.stamped.jsonl", "F_rows.jsonl"):
                _sp = OFFICIAL / _src
                if _sp.is_file():
                    _tmp = _exp / f".{_src}.tmp"
                    _sh.copyfile(_sp, _tmp)
                    _tmp.replace(_exp / _src)
            _lc = _exp / ".last_close.json.tmp"
            _lc.write_text(json.dumps({
                "ts": _now(), "tick_id": str(close["tick_id"]),
                "f_row_id": str(close["f_row_id"]),
                "contract_id": str(close["contract_id"]),
                "official_state_hash": row["official_state_hash"],
            }), encoding="utf-8")
            _lc.replace(_exp / "last_close.json")
        except Exception as _ee:  # noqa: BLE001
            try:
                (QUARANTINE / "export_on_close.warn.json").write_text(
                    json.dumps({"ts": _now(),
                                "export_failed_nonfatal": repr(_ee),
                                "tick_id": str(close.get("tick_id"))}))
            except Exception:
                pass
    proposal_path.unlink(missing_ok=True)
    return {"verdict": "pass", "proposal_id": pid,
            "proposal_body_sha256": body_sha,
            "official_state_hash": row["official_state_hash"],
            "membrane_stamp": v.stamp,
            "close_verified": bool(is_close)}


def scan_once() -> list[dict]:
    _ensure()
    # GP-241 #2: relay worker-produced verdicts into the inbox FIRST
    # (so a verdict and a re-submitted close in the same tick still
    # resolve in order), then process the inbox.
    _ingest_verdicts()
    out = []
    for f in sorted(INBOX.glob("*.json")):
        out.append(process_one(f))
    return out


def main() -> int:
    import sys
    _ensure()
    once = "--once" in sys.argv
    print(f"verificator daemon — store={STORE} (OUTSIDE repo) "
          f"mode={'once' if once else 'loop'}")
    while True:
        results = scan_once()
        for r in results:
            print(json.dumps(r))
        if once:
            return 0
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())

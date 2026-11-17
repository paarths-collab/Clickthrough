#!/usr/bin/env python3
"""Check .userflow/flows.yaml for gaps an agent tends to leave.

Usage:
    python3 uf-check.py [--stage discover|flows|test|evaluate] [--file PATH]

Stages add checks as the work moves on:
    discover  ids, types, every page has a way in or is flagged, nav leads somewhere
    flows     + every surface is in a flow, every goal has a flow, routes are listed
    test      + every flow has a test file that exists
    evaluate  + pass needs evidence files that exist, fail needs a class and
              finding; prints the verdict

With no --stage it runs every check (evaluate). Evidence and test paths are
relative to the project root (the folder that holds .userflow/).

Exit code 1 if there are errors. Warnings do not fail the check. Needs PyYAML
(`pip install pyyaml`). If you cannot run this, do the same checks by hand
and log a tool gap.
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    sys.exit("uf-check needs PyYAML: pip install pyyaml")

STAGES = ["discover", "flows", "test", "evaluate"]
SURFACE_TYPES = {"nav", "page", "form", "action", "message", "empty_state",
                 "endpoint", "mcp_tool", "cli", "job", "notification", "data"}
SOURCES = {"intent", "code", "both"}
PRIORITIES = {"P0", "P1", "P2"}
VARIANTS = {"normal", "alternate", "wrong_input", "not_allowed", "interrupted",
            "empty", "return_visit", "handoff"}
STATUSES = {"untested", "pass", "fail", "unverified", "blocked", "likely_broken"}
CONFIDENCE = {"high", "medium", "low"}
CLASSES = {"FLOW_BROKEN", "SOFTWARE_BUG", "INTEGRATION", "MISSING_FEATURE",
           "ENV_BLOCKED", "TEST_DEFECT", "TOOL_GAP"}
# Surfaces a user reaches by clicking, so they need a stated way in.
NEEDS_REACH = {"page", "form", "action"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=STAGES, default="evaluate")
    parser.add_argument("--file", default=".userflow/flows.yaml")
    args = parser.parse_args()
    stage = STAGES.index(args.stage)
    root = os.path.dirname(os.path.dirname(os.path.abspath(args.file)))

    try:
        with open(args.file, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as err:
        sys.exit(f"ERROR cannot read {args.file}: {err}")

    errors, warnings = [], []
    err, warn = errors.append, warnings.append

    def items(key):
        value = data.get(key) or []
        if not isinstance(value, list):
            err(f"`{key}` must be a list")
            return []
        return [v for v in value if isinstance(v, dict)]

    def ids(key):
        seen = Counter(i.get("id") for i in items(key))
        for ident, count in seen.items():
            if ident is None:
                err(f"an entry in `{key}` has no id")
            elif count > 1:
                err(f"duplicate id {ident} in `{key}`")
        return {i for i in seen if i is not None}

    product = data.get("product") or {}
    if not product.get("purpose"):
        err("product.purpose is empty: write what the product is for before mapping it")
    if not product.get("intent_sources"):
        warn("product.intent_sources is empty: flows built from code alone miss features that were never built")
    run = data.get("run") or {}
    for field in ("boot", "base_url"):
        if not run.get(field):
            warn(f"run.{field} is empty (uf-preflight fills this in)")

    persona_ids, surface_ids = ids("personas"), ids("surfaces")
    goal_ids, flow_ids = ids("goals"), ids("flows")
    if not persona_ids:
        err("no personas")
    if not surface_ids:
        err("no surfaces")

    surfaces, flows = items("surfaces"), items("flows")

    # ---- surfaces ---------------------------------------------------------
    for s in surfaces:
        sid = s.get("id")
        if s.get("type") not in SURFACE_TYPES:
            err(f"{sid}: type `{s.get('type')}` is not one of {sorted(SURFACE_TYPES)}")
        if s.get("source") not in SOURCES:
            err(f"{sid}: source must be intent, code or both")
        for p in s.get("personas") or []:
            if p not in persona_ids:
                err(f"{sid}: unknown persona {p}")
        if s.get("type") in NEEDS_REACH and s.get("source") != "intent":
            reach = s.get("reach")
            if reach in (None, ""):
                err(f"{sid} ({s.get('name')}): `reach` is empty. Say how a user gets here by clicking, or `none`")
            elif str(reach).strip().lower() == "none":
                warn(f"{sid} ({s.get('name')}): no way in from the UI. Report it as a finding")
        # A nav item that was promised and is absent has nothing to lead to;
        # the "promised, not found" warning below covers it.
        if s.get("type") == "nav" and s.get("source") != "intent":
            target = s.get("leads_to")
            if target in (None, ""):
                err(f"{sid} ({s.get('name')}): nav item needs `leads_to` (a surface id, or `nowhere`)")
            elif target == "nowhere":
                warn(f"{sid} ({s.get('name')}): nav item leads nowhere. Report it as a finding")
            elif target not in surface_ids:
                err(f"{sid}: leads_to {target} is not a surface id")
        if s.get("source") == "intent":
            warn(f"{sid} ({s.get('name')}): promised in the intent, not found in the product")

    for area in items("areas"):
        if area.get("status") == "pending":
            warn(f"area {area.get('id')} ({area.get('name')}) is not mapped yet")

    # ---- flows ------------------------------------------------------------
    if stage >= 1:
        if not flows:
            err("no flows")
        used = set()
        routes = defaultdict(list)
        variants = Counter()
        for f in flows:
            fid = f.get("id")
            if f.get("persona") not in persona_ids:
                err(f"{fid}: unknown persona {f.get('persona')}")
            if f.get("goal") not in goal_ids:
                err(f"{fid}: goal `{f.get('goal')}` is not in `goals`")
            if f.get("priority") not in PRIORITIES:
                err(f"{fid}: priority must be P0, P1 or P2")
            if f.get("variant") not in VARIANTS:
                err(f"{fid}: variant `{f.get('variant')}` is not one of {sorted(VARIANTS)}")
            if f.get("status") not in STATUSES:
                err(f"{fid}: status `{f.get('status')}` is not one of {sorted(STATUSES)}")
            if not f.get("start"):
                err(f"{fid}: `start` is empty. Say where the user begins")
            steps = f.get("steps") or []
            if not steps:
                err(f"{fid}: no steps")
            for n, step in enumerate(steps, 1):
                if not isinstance(step, dict) or not step.get("do") or not step.get("see"):
                    err(f"{fid}: step {n} needs both `do` and `see`")
            for sid in f.get("surfaces") or []:
                if sid not in surface_ids:
                    err(f"{fid}: unknown surface {sid}")
                used.add(sid)
            routes[f.get("goal")].append(f)
            variants[f.get("variant")] += 1

        for s in surfaces:
            if s.get("id") not in used and not s.get("excluded"):
                err(f"{s.get('id')} ({s.get('name')}) is in no flow. Add a flow, or set `excluded: <reason>`")
        for g in items("goals"):
            mine = routes.get(g.get("id"), [])
            if not mine:
                err(f"goal {g.get('id')} ({g.get('title')}) has no flow")
            elif not any(f.get("variant") in ("normal", "alternate", "empty") for f in mine):
                warn(f"goal {g.get('id')} ({g.get('title')}) has no flow where the user "
                     "simply succeeds (`normal`, `alternate` or `empty`)")
        missing = VARIANTS - set(variants) - {"alternate", "handoff"}
        if missing:
            warn(f"no flow at all for variant(s): {', '.join(sorted(missing))}")

    # ---- tests ------------------------------------------------------------
    if stage >= 2:
        for f in flows:
            if f.get("status") in ("blocked", "likely_broken"):
                continue
            test_file = f.get("test_file")
            if not test_file:
                err(f"{f.get('id')}: no test_file")
            elif not os.path.exists(os.path.join(root, test_file)):
                err(f"{f.get('id')}: test file does not exist: {test_file}")

    # ---- results ----------------------------------------------------------
    if stage >= 3:
        for f in flows:
            fid, status = f.get("id"), f.get("status")
            last = f.get("last_run") or {}
            evidence = last.get("evidence") or []
            if isinstance(evidence, str):
                evidence = [evidence]
            if status == "pass" and not evidence:
                err(f"{fid}: status is pass with no evidence. Use `unverified`")
            gone = [str(p) for p in evidence if not os.path.exists(os.path.join(root, str(p)))]
            if gone and status == "pass":
                err(f"{fid}: pass, but evidence not found (paths are relative to the "
                    f"project root): {', '.join(gone)}")
            elif gone:
                warn(f"{fid}: evidence not found (paths are relative to the project "
                     f"root): {', '.join(gone)}")
            if status in ("pass", "fail") and not last.get("commit"):
                err(f"{fid}: {status} without last_run.commit")
            if status == "likely_broken" and f.get("confidence") not in CONFIDENCE:
                err(f"{fid}: likely_broken needs `confidence: high | medium | low`")
            if status in ("fail", "blocked", "likely_broken"):
                if f.get("failure_class") not in CLASSES:
                    err(f"{fid}: {status} needs a failure_class from {sorted(CLASSES)}")
                if not f.get("finding"):
                    err(f"{fid}: {status} needs a one-line `finding`")
            if status == "untested":
                warn(f"{fid}: still untested")

    # ---- summary ----------------------------------------------------------
    print(f"{args.file}: {len(persona_ids)} personas, {len(surface_ids)} surfaces, "
          f"{len(goal_ids)} goals, {len(flow_ids)} flows  (stage: {args.stage})")
    if stage >= 1 and flows:
        multi = {g: fl for g, fl in routes.items()
                 if len({f.get('route') for f in fl if f.get('variant') in ('normal', 'alternate')}) > 1}
        for goal, fl in sorted(multi.items(), key=lambda kv: str(kv[0])):
            listing = "; ".join(f"{f.get('id')} {f.get('route')} [{f.get('status')}]"
                                for f in fl if f.get("variant") in ("normal", "alternate"))
            print(f"  goal {goal} has more than one route: {listing}")
        for priority in sorted(PRIORITIES):
            counts = Counter(f.get("status") for f in flows if f.get("priority") == priority)
            total = sum(counts.values())
            if total:
                detail = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
                print(f"  {priority}: {total} flows ({detail})")
    for line in warnings:
        print(f"WARN  {line}")
    for line in errors:
        print(f"ERROR {line}")

    if stage >= 3 and flows:
        p0 = [f for f in flows if f.get("priority") == "P0"]
        if errors:
            verdict = "CANNOT TELL (fix the errors above first)"
        elif not p0:
            verdict = "CANNOT TELL (no P0 flows defined)"
        elif any(f.get("status") == "fail" for f in p0):
            verdict = "NOT READY"
        elif any(f.get("status") == "likely_broken" for f in p0):
            n = sum(1 for f in p0 if f.get("status") == "likely_broken")
            verdict = (f"CANNOT TELL, likely NOT READY ({n} P0 flow(s) look broken "
                       "in code; not run)")
        elif all(f.get("status") == "pass" for f in p0):
            verdict = "READY"
        else:
            verdict = "CANNOT TELL (P0 flows not verified)"
        print(f"Verdict from the registry: {verdict}")

    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

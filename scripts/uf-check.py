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
import fnmatch
import json
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
VARIANTS = {"normal", "alternate", "wrong_input", "not_allowed", "abuse", "interrupted",
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
        if area.get("status") not in ("mapped", "tested", "excluded"):
            warn(f"area {area.get('id')} ({area.get('name')}) is not covered yet "
                 "(status pending); the verdict cannot be READY until it is")

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
    shallow = []  # P0 components / workflows with no uf-cases coverage
    if stage >= 2:
        deep_types = {"page", "form", "action", "endpoint", "mcp_tool", "cli"}
        p0_surfaces = {sid for f in flows if f.get("priority") == "P0" for sid in (f.get("surfaces") or [])}
        for s in surfaces:
            sid = s.get("id")
            if sid not in p0_surfaces or s.get("type") not in deep_types or s.get("excluded"):
                continue
            path = s.get("cases")
            if not path:
                shallow.append(sid)
            elif not os.path.exists(os.path.join(root, str(path))):
                warn(f"{sid}: cases file does not exist: {path}")
        if shallow:
            listing = ", ".join(str(x) for x in shallow[:20]) + (" ..." if len(shallow) > 20 else "")
            warn(f"{len(shallow)} P0 components have no `cases` file yet (uf-cases): {listing}")
    if stage >= 2:
        for f in flows:
            if f.get("status") in ("blocked", "likely_broken"):
                continue
            test_file = f.get("test_file")
            if not test_file and f.get("status") in (None, "untested"):
                continue  # work not done yet: counted in "tested X of Y", not an error
            if not test_file:
                err(f"{f.get('id')}: {f.get('status')} but no test_file")
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

    # ---- priority discipline --------------------------------------------
    if stage >= 1 and len(flows) >= 20:
        p0_share = sum(1 for f in flows if f.get("priority") == "P0") / len(flows)
        if p0_share > 0.30:
            warn(f"{p0_share:.0%} of flows are P0: P0 is for the core job, sign-in, money, other tenants' "
                 "data, permissions and data loss; re-rank (uf-catalog section 4) so the worst bugs are found first")

    # ---- bug register -----------------------------------------------------
    bugs_path = os.path.join(root, ".userflow", "bugs.yaml")
    bug_list = []
    if stage >= 3:
        failing = [f for f in flows if f.get("status") in ("fail", "likely_broken")]
        if os.path.exists(bugs_path):
            try:
                bug_list = (yaml.safe_load(open(bugs_path, encoding="utf-8")) or {}).get("bugs") or []
            except yaml.YAMLError as exc:
                err(f".userflow/bugs.yaml is not valid YAML: {exc}")
            bug_ids = {b.get("id") for b in bug_list if isinstance(b, dict)}
            for b in bug_list:
                if not isinstance(b, dict):
                    continue
                if b.get("severity") not in ("critical", "high", "medium", "low"):
                    err(f"bug {b.get('id')}: severity must be critical, high, medium or low")
                if b.get("status") not in ("open", "fixed", "wont_fix", "duplicate"):
                    err(f"bug {b.get('id')}: status must be open, fixed, wont_fix or duplicate")
                if not b.get("title"):
                    err(f"bug {b.get('id')}: needs a title (what a user or attacker experiences)")
                if b.get("status") == "fixed" and not b.get("fixed_in"):
                    err(f"bug {b.get('id')}: fixed needs fixed_in (commit and the run that proved it)")
                for fid in b.get("flows") or []:
                    if fid not in flow_ids:
                        err(f"bug {b.get('id')}: flow {fid} is not in flows.yaml")
                if b.get("how_known") not in ("ran", "traced", "read"):
                    err(f"bug {b.get('id')}: how_known must be ran, traced or read")
                elif b.get("how_known") in ("traced", "read") and b.get("status") == "open":
                    if not b.get("where"):
                        err(f"bug {b.get('id')}: {b.get('how_known')} needs `where` (file and line)")
                    if b.get("confidence") not in ("high", "medium", "low"):
                        err(f"bug {b.get('id')}: {b.get('how_known')} needs confidence: high, medium or low")
                if b.get("how_known") == "ran" and b.get("status") in ("open", "fixed"):
                    proof = [str(x) for x in (b.get("proof") or [])]
                    present = [x for x in proof if os.path.exists(os.path.join(root, x))]
                    if not present:
                        err(f"bug {b.get('id')}: found by running but has no proof file; the verifier records "
                            "a video and trace (screens) or a transcript (API, CLI) in .userflow/proof/")
                    elif len(present) < len(proof):
                        err(f"bug {b.get('id')}: proof file missing: "
                            + ", ".join(x for x in proof if x not in present))
                    recording = (".webm", ".mp4", ".mov", ".gif", ".cast", ".zip", ".txt", ".har", ".log", ".json")
                    if present and not any(x.lower().endswith(recording) for x in present):
                        warn(f"bug {b.get('id')}: proof has no recording (video, trace or transcript), "
                             "only images")
            for f in failing:
                if not f.get("bug"):
                    err(f"{f.get('id')}: {f.get('status')} but names no bug; add it to .userflow/bugs.yaml")
                elif f.get("bug") not in bug_ids:
                    err(f"{f.get('id')}: bug {f.get('bug')} is not in .userflow/bugs.yaml")
        elif failing:
            warn(f"{len(failing)} failing flows but no .userflow/bugs.yaml: list every bug once there")

    # ---- workflows must be mapped before testing -------------------------
    if stage >= 1 and flows:
        p0_goal_ids = {f.get("goal") for f in flows if f.get("priority") == "P0"}
        for g in items("goals"):
            gid = g.get("id")
            if gid not in p0_goal_ids:
                continue
            card = g.get("cases")
            if not card:
                err(f"goal {gid} ({g.get('title')}): P0 workflow has no workflow card; map it "
                    "(uf-catalog section 3) before testing")
            elif not os.path.exists(os.path.join(root, str(card))):
                err(f"goal {gid}: workflow card does not exist: {card}")

    # ---- coverage against the code map ----------------------------------
    uncovered = []
    inv_path = os.path.join(root, ".userflow", "inventory.json")
    if stage >= 1 and os.path.exists(inv_path):
        try:
            inventory = json.load(open(inv_path, encoding="utf-8")).get("items", [])
        except (ValueError, OSError) as exc:
            inventory = []
            warn(f".userflow/inventory.json could not be read: {exc}")
        patterns = []
        for s in surfaces:
            for value in [s.get("location")] + list(s.get("covers") or []):
                if value:
                    patterns.append(str(value).strip().rstrip("/") or "/")

        def covered(item):
            what = str(item.get("what", "")).strip()
            path_part = what.split(" ", 1)[1] if " " in what else what
            where = str(item.get("where", "")).rsplit(":", 1)[0]
            for pat in patterns:
                for candidate in (what, path_part.rstrip("/") or "/", where):
                    if candidate == pat or fnmatch.fnmatchcase(candidate, pat):
                        return True
            return False

        kinds = {"page", "route", "cli", "mcp_tool", "job", "webhook"}
        for item in inventory:
            if item.get("kind") in kinds and not item.get("test") and not covered(item):
                uncovered.append(item)
        if uncovered:
            by_kind = Counter(i["kind"] for i in uncovered)
            summary = ", ".join(f"{k} {v}" for k, v in sorted(by_kind.items()))
            listing = "; ".join(f"{i['kind']} {i['what']} ({i['where']})" for i in uncovered[:15])
            more = f" ... and {len(uncovered) - 15} more" if len(uncovered) > 15 else ""
            err(f"{len(uncovered)} entry points in the code map belong to no surface ({summary}). "
                f"Add surfaces (use `covers:` globs to group), or a surface with `excluded:` and a "
                f"reason: {listing}{more}")
    elif stage >= 1:
        warn("no .userflow/inventory.json: run uf-inventory.py --json --out .userflow/inventory.json "
             "so coverage can be checked against the code")

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
    tested_statuses = {"pass", "fail", "likely_broken", "blocked"}
    untested = [f for f in flows if f.get("status") not in tested_statuses]
    if stage >= 3 and untested:
        by_priority = Counter(f.get("priority") for f in untested)
        warn(f"{len(untested)} flows not tested yet ("
             + ", ".join(f"{k} {v}" for k, v in sorted(by_priority.items(), key=lambda kv: str(kv[0])))
             + "): the verdict cannot be READY; carry on with uf-parallel or write .userflow/next.md")
    if stage >= 1 and flows:
        done = len(flows) - len(untested)
        print(f"  Coverage: tested {done} of {len(flows)} flows"
              + (f"; {len(untested)} still to test" if untested else ""))
    if stage >= 3 and flows:
        by_goal = defaultdict(list)
        for f in flows:
            by_goal[f.get("goal")].append(f)
        for goal, fl in sorted(by_goal.items(), key=lambda kv: str(kv[0])):
            passed = [f for f in fl if f.get("status") == "pass"]
            open_routes = [f for f in fl if f.get("status") in ("untested", "unverified", "blocked", "likely_broken", None)]
            if passed and open_routes:
                warn(f"goal {goal}: only partly verified - do not report it as working; "
                     "routes not run: " + ", ".join(f"{f.get('id')} {f.get('route') or ''} [{f.get('status')}]"
                                                   for f in open_routes[:6]))
    if bug_list:
        open_bugs = [b for b in bug_list if isinstance(b, dict) and b.get("status") == "open"]
        sev = Counter(b.get("severity") for b in open_bugs)
        order = ["critical", "high", "medium", "low"]
        print(f"  Bugs: {len(open_bugs)} open ("
              + ", ".join(f"{k} {sev[k]}" for k in order if sev[k]) + f"), "
              + f"{sum(1 for b in bug_list if isinstance(b, dict) and b.get('status') == 'fixed')} fixed")
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
            open_areas = [a.get("id") for a in items("areas")
                          if a.get("status") not in ("mapped", "tested", "excluded")]
            if untested:
                verdict = (f"CANNOT TELL (every P0 flow passed, but tested only "
                           f"{len(flows) - len(untested)} of {len(flows)} flows)")
            elif not open_areas and shallow:
                verdict = ("CANNOT TELL (every P0 flow written passed, but these P0 components "
                           "were not tested in depth with uf-cases: "
                           + ", ".join(str(x) for x in shallow[:10])
                           + (" ..." if len(shallow) > 10 else "") + ")")
            elif open_areas:
                verdict = ("CANNOT TELL (every P0 flow written passed, but areas not covered: "
                           + ", ".join(str(a) for a in open_areas) + ")")
            else:
                verdict = "READY"
        else:
            verdict = "CANNOT TELL (P0 flows not verified)"
        print(f"Verdict from the registry: {verdict}")

    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

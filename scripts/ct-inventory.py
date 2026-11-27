#!/usr/bin/env python3
"""Dissect a codebase into the things a user (or an attacker) can reach.

Usage:
    python3 ct-inventory.py [PROJECT_DIR] [--json] [--out FILE]

Walks the source tree and lists, with file:line:
    page        UI routes and screens
    route       HTTP / RPC endpoints (method + path)
    cli         command-line commands and subcommands
    mcp_tool    tools an AI agent can call
    job         scheduled jobs, queues, workers, cron
    webhook     inbound webhook receivers
    outbound    calls this product makes to other systems (incl. user-supplied URLs)
    email       places that send email / SMS / push
    data_write  deletes and other destructive data writes
    env         environment variables the code reads

It is a heuristic starting map for `ct-discover` and `ct-security`, not a
complete or exact inventory: frameworks it does not know are missed, and
some matches are false. Check each entry against the code. No network
access, no writes outside --out. Needs only Python 3.
"""
import argparse
import ast
from ct_core import identity
import json
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", "out", "target", ".next",
             ".nuxt", ".svelte-kit", "__pycache__", ".venv", "venv", "env", ".tox",
             "coverage", ".turbo", ".cache", "bin", "obj", ".gradle", ".idea",
             ".clickthrough", "clickthrough-tests", ".claude", ".agents", "Pods", "DerivedData"}
CODE_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".rs",
            ".java", ".kt", ".kts", ".scala", ".cs", ".php", ".ex", ".exs", ".swift",
            ".html", ".c", ".cc", ".cpp", ".h", ".hpp", ".vue", ".svelte", ".dart", ".sql", ".astro", ".mdx"}
# A file is test code when its own name says so (x.test.ts, x_test.go,
# test_x.py, XTest.java, x.spec.js, fixtures, stories) or it sits in a test
# folder that is not part of the app's routes. A folder merely named
# "tests" inside app/, pages/ or routes/ is a real screen (e.g. "Test runs").
TEST_FILE = re.compile(r"([._-](test|spec|fixtures?|mocks?|stories|story)\.[a-z]+$)|"
                       r"(^test_[^/]+\.py$)|(_test\.(go|py|rb|exs)$)|((Test|Tests|IT|Spec)\.(java|kt|cs|scala)$)", re.I)
TEST_DIR = re.compile(r"(^|/)(tests?|__tests__|spec|specs|e2e|fixtures?|__mocks__|mocks?|testdata|test-data)(/|$)", re.I)
ROUTE_DIR = re.compile(r"(^|/)(app|pages|routes|views|screens)/")


def is_test_path(rel):
    rel = rel.replace(os.sep, "/")
    name = rel.rsplit("/", 1)[-1]
    if TEST_FILE.search(name):
        return True
    if TEST_DIR.search(rel):
        # Inside the app's route tree, a "tests" folder is a page, not test code.
        before = TEST_DIR.search(rel).start()
        return not ROUTE_DIR.search(rel[:before + 1])
    return False
MAX_BYTES = 1_500_000

M = r"(get|post|put|patch|delete|options|head|all)"
def flask_route(m):
    """@app.route('/x', methods=['POST', 'GET']) -> one entry per method; @app.get('/x') -> GET."""
    if m.group(1):
        return f"{m.group(1).upper()} {m.group(2)}"
    methods = re.search(r"methods\s*=\s*[\[(]([^\])]*)[\])]", m.string)
    if methods:
        names = [n.strip(" '\"").upper() for n in methods.group(1).split(",") if n.strip(" '\"")]
        if names:
            return f"{'|'.join(names)} {m.group(2)}"
    return f"GET {m.group(2)}"  # Flask's default when methods is not given


PATTERNS = [
    # ---- HTTP routes ----------------------------------------------------
    ("route", re.compile(r"\b(?:app|router|server|api|r|e|g|mux|fastify)\s*\.\s*" + M +
                         r"\s*\(\s*['\"`]([^'\"`]+)", re.I), lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    ("route", re.compile(r"@(?:app|router|bp|blueprint|api|\w+_router)\s*\.\s*(?:route|" + M +
                         r")\s*\(\s*['\"]([^'\"]+)", re.I), flask_route),
    ("route", re.compile(r"@(Get|Post|Put|Patch|Delete|Request)Mapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]?([^'\")]*)"),
     lambda m: f"{m.group(1).upper().replace('REQUEST', 'ANY')} {m.group(2) or '/'}"),
    ("route", re.compile(r"@(Get|Post|Put|Patch|Delete|All)\s*\(\s*['\"]?([^'\")]*)"),
     lambda m: f"{m.group(1).upper()} {m.group(2) or '/'}"),
    ("route", re.compile(r"\b(?:path|re_path|url)\s*\(\s*r?['\"]([^'\"]*)['\"]\s*,"), lambda m: f"ANY /{m.group(1)}"),
    ("route", re.compile(r"\b(get|post|put|patch|delete)\s+['\"](/[^'\"]*)['\"]"), lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    ("route", re.compile(r"\bHandleFunc\s*\(\s*\"([^\"]+)\""), lambda m: f"ANY {m.group(1)}"),
    ("route", re.compile(r"\.route\s*\(\s*\"([^\"]+)\"\s*,\s*(get|post|put|patch|delete)"),
     lambda m: f"{m.group(2).upper()} {m.group(1)}"),
    ("route", re.compile(r"#\[(get|post|put|patch|delete)\s*\(\s*\"([^\"]+)\""), lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    ("route", re.compile(r"\bMap(Get|Post|Put|Patch|Delete)\s*\(\s*\"([^\"]+)\""), lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    ("route", re.compile(r"\bRoute::(get|post|put|patch|delete|any)\s*\(\s*['\"]([^'\"]+)"),
     lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    ("route", re.compile(r"method\s*===?\s*['\"](GET|POST|PUT|PATCH|DELETE)['\"]\s*&&\s*\(?\s*\w+\s*===?\s*['\"](/[^'\"]+)", re.I),
     lambda m: f"{m.group(1).upper()} {m.group(2)}"),
    ("route", re.compile(r"method\s*===?\s*['\"](GET|POST|PUT|PATCH|DELETE)['\"]\s*&&\s*\(?\s*\w+\s*=\s*\w+\.match\(\s*/\^?((?:\\/|[^/])+)/", re.I),
     lambda m: f"{m.group(1).upper()} {m.group(2).replace(chr(92), '')}"),
    ("route", re.compile(r"^\s*export\s+(?:async\s+)?(?:function|const)\s+(GET|POST|PUT|PATCH|DELETE)\b"),
     lambda m: f"{m.group(1)} <file route>"),
    # ---- CLI ------------------------------------------------------------
    ("cli", re.compile(r"\.add_parser\s*\(\s*['\"]([^'\"]+)"), lambda m: m.group(1)),
    ("cli", re.compile(r"@(?:\w+\.)?(?:command|group)\s*\(\s*(?:name\s*=\s*)?['\"]?([\w:-]*)"), lambda m: m.group(1) or "<command>"),
    ("cli", re.compile(r"\.command\s*\(\s*['\"]([^'\"]+)"), lambda m: m.group(1)),
    ("cli", re.compile(r"#\[(?:command|clap)\s*\(([^)]*)\)"), lambda m: m.group(1)[:60]),
    ("cli", re.compile(r"&cobra\.Command\s*\{|\bUse:\s*\"([^\"]+)\""), lambda m: (m.group(1) or "<cobra command>")),
    # ---- MCP tools ------------------------------------------------------
    ("mcp_tool", re.compile(r"\.(?:tool|registerTool|addTool)\s*\(\s*['\"]([\w.-]+)"), lambda m: m.group(1)),
    ("mcp_tool", re.compile(r"@(?:mcp|server|app)\.tool\s*\("), lambda m: "<decorated tool>"),
    ("mcp_tool", re.compile(r"\bname:\s*['\"]([a-z][a-z0-9_]+)['\"]\s*,\s*description:"), lambda m: m.group(1)),
    # ---- jobs -----------------------------------------------------------
    ("job", re.compile(r"\b(cron\.schedule|schedule\.every|@Scheduled|@periodic_task|@shared_task|"
                       r"@celery\.task|@app\.task|BullMQ|new Worker\(|new Queue\(|setInterval\(|"
                       r"add_job\(|sidekiq_options|perform_later|tokio::spawn|cron\s*:)", re.I), lambda m: m.group(1)),
    # ---- webhooks -------------------------------------------------------
    ("webhook", re.compile(r"['\"`](/[\w/:\[\].{}$-]*webhook[\w/:\[\].{}$-]*)['\"`]", re.I), lambda m: m.group(1)[:80]),
    # ---- outbound -------------------------------------------------------
    ("outbound", re.compile(r"\b(fetch|axios(?:\.(?:get|post|put|patch|delete|request))?|requests\.(?:get|post|put|delete|request)|"
                            r"httpx\.(?:get|post|put|delete|request)|http\.(?:Get|Post)|reqwest::(?:get|Client)|"
                            r"urllib\.request\.urlopen|got|ky)\s*\(\s*([`'\"]?[^,)\n]{0,60})"),
     lambda m: f"{m.group(1)}({m.group(2).strip()}"),
    # ---- email / notifications -----------------------------------------
    ("email", re.compile(r"\b(sendMail|send_mail|resend\.\w+|sgMail|nodemailer|ses\.send|"
                         r"mailer\.\w+|EmailMessage|SmtpClient|twilio|sendSms|send_sms|webpush|"
                         r"generateLink|inviteUserByEmail|queueMail|enqueueEmail|sendEmail|send_email)", re.I), lambda m: m.group(1)),
    # ---- destructive writes --------------------------------------------
    ("data_write", re.compile(r"(\bDELETE\s+FROM\s+\w+|\bTRUNCATE\b|\bDROP\s+TABLE\b|\.delete\(\)|"
                              r"\.destroy\(|\.deleteMany\(|\.remove\(\s*\{|\.delete_many\(|"
                              r"\.delete\(\s*[\w.]+\s*[,)])"), lambda m: m.group(1)[:50]),
    # ---- env ------------------------------------------------------------
    ("env", re.compile(r"(?:process\.env\.|import\.meta\.env\.|os\.environ(?:\.get)?\(?\[?['\"]|"
                       r"os\.getenv\(['\"]|getenv\(\"|env::var\(\"|System\.getenv\(\"|ENV\[['\"])([A-Z][A-Z0-9_]{2,})"),
     lambda m: m.group(1)),
]

PAGE_FILE = re.compile(r"(^|/)(app|pages|routes|views|screens)/(.+?)/?(page|index|\+page|route)?\."
                       r"(tsx|jsx|ts|js|vue|svelte|astro|mdx)$")


def page_from_path(rel):
    rel = rel.replace(os.sep, "/")
    m = re.search(r"(?:^|/)app/(.*?)/?page\.(tsx|jsx|ts|js|mdx)$", rel)
    if m:  # Next.js app router: drop (groups)
        parts = [p for p in m.group(1).split("/") if p and not (p.startswith("(") and p.endswith(")"))]
        return "/" + "/".join(parts)
    m = re.search(r"(?:^|/)pages/(.+)\.(tsx|jsx|ts|js|vue|svelte|astro|mdx)$", rel)
    if m and not m.group(1).startswith(("_", "api/")):
        route = re.sub(r"/?index$", "", m.group(1))
        return "/" + route
    m = re.search(r"(?:^|/)routes/(.*?)/?\+page\.svelte$", rel)
    if m:
        return "/" + m.group(1)
    return None


def api_from_path(rel):
    rel = rel.replace(os.sep, "/")
    m = re.search(r"(?:^|/)app/(.*?)/route\.(ts|js|tsx|jsx)$", rel)
    if m:
        parts = [p for p in m.group(1).split("/") if p and not (p.startswith("(") and p.endswith(")"))]
        return "/" + "/".join(parts)
    m = re.search(r"(?:^|/)pages/(api/.+)\.(ts|js)$", rel)
    if m:
        return "/" + re.sub(r"/?index$", "", m.group(1))
    return None


def scan(root, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else []
    found = []
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d in (".github",)]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            ext = os.path.splitext(name)[1].lower()
            if ext not in CODE_EXT and name not in ("vercel.json", "crontab"):
                if ext in (".yaml", ".yml", ".toml", ".json", ".sh", ".graphql", ".proto"):
                    diagnostics.append({"path": rel, "reason": "no static adapter for this file; reconcile with runtime/docs"})
                continue
            is_test = is_test_path(rel)
            page = page_from_path(rel)
            if page and not is_test:
                found.append({"kind": "page", "what": page or "/", "where": f"{rel}:1", "test": False})
            api_path = api_from_path(rel)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    diagnostics.append({"path": rel, "reason": "file exceeds scan size limit"})
                    continue
                with open(path, encoding="utf-8", errors="replace") as handle:
                    lines = handle.readlines()
            except OSError:
                diagnostics.append({"path": rel, "reason": "unreadable file"})
                continue
            text = "".join(lines)
            mcp_file = ("tools/list" in text or "McpServer" in text or "modelcontextprotocol" in text
                        or "FastMCP" in text) and not is_test
            if name.endswith(".html") and not is_test:
                found.append({"kind": "page", "what": "/" + name, "where": f"{rel}:1", "test": False})
            for number, line in enumerate(lines, 1):
                if len(line) > 600:
                    diagnostics.append({"path": f"{rel}:{number}", "reason": "line exceeds scan length limit"})
                    continue
                if mcp_file:
                    tool = re.search(r"\bname:\s*['\"]([a-z][a-z0-9_]+)['\"]\s*,?\s*$", line)
                    if tool and ("mcp_tool", tool.group(1), rel) not in seen:
                        seen.add(("mcp_tool", tool.group(1), rel))
                        found.append({"kind": "mcp_tool", "what": tool.group(1), "where": f"{rel}:{number}", "test": False})
                for kind, pattern, label in PATTERNS:
                    if ext == ".sql" and kind not in ("data_write", "job"):
                        continue
                    for match in pattern.finditer(line):
                        try:
                            what = label(match).strip()
                        except (IndexError, AttributeError):
                            what = match.group(0)[:60]
                        if kind == "outbound" and re.search(r"\([`'\"]/", what):
                            continue  # relative URL: the product calling itself
                        if kind == "route" and what.endswith("<file route>") and api_path:
                            what = what.replace("<file route>", api_path)
                        key = (kind, what, rel) if kind == "env" else (kind, what, rel, number)
                        if key in seen:
                            continue
                        seen.add(key)
                        found.append({"kind": kind, "what": what, "where": f"{rel}:{number}", "test": is_test})
            if api_path and "/pages/" in "/" + rel and not is_test:
                found.append({"kind": "route", "what": "ANY " + api_path, "where": f"{rel}:1", "test": False})
            if name == "crontab":
                for number, line in enumerate(lines, 1):
                    if line.strip() and not line.lstrip().startswith("#") and (line.lstrip().startswith("@") or len(line.split()) >= 6):
                        found.append({"kind": "job", "what": line.strip(), "where": f"{rel}:{number}", "test": is_test})
            if ext == ".py":
                try:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            continue
                        for dec in node.decorator_list:
                            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute) or dec.func.attr not in ("route", "get", "post", "put", "patch", "delete", "head", "options") or not dec.args:
                                continue
                            if not isinstance(dec.args[0], ast.Constant) or not isinstance(dec.args[0].value, str):
                                diagnostics.append({"path": f"{rel}:{dec.lineno}", "reason": "dynamic route needs runtime reconciliation"})
                                continue
                            methods = [dec.func.attr.upper()] if dec.func.attr != "route" else ["GET"]
                            for kw in dec.keywords:
                                if kw.arg == "methods":
                                    methods = ast.literal_eval(kw.value)
                            found[:] = [i for i in found if not (i["kind"] == "route" and i["where"].startswith(rel + ":") and dec.lineno <= int(i["where"].rsplit(":", 1)[1]) <= dec.end_lineno)]
                            for method in methods:
                                found.append({"kind": "route", "what": str(method).upper() + " " + dec.args[0].value, "where": f"{rel}:{dec.lineno}", "test": is_test})
                except (SyntaxError, ValueError, TypeError):
                    diagnostics.append({"path": rel, "reason": "Python AST or dynamic methods need runtime reconciliation"})
            if name == "vercel.json":
                try:
                    data = json.load(open(path, encoding="utf-8"))
                    for cron in data.get("crons", []):
                        found.append({"kind": "job", "what": f"cron {cron.get('schedule')} {cron.get('path')}",
                                      "where": f"{rel}:1", "test": False})
                except (ValueError, OSError):
                    pass
    return found


ORDER = ["page", "route", "cli", "mcp_tool", "job", "webhook", "outbound", "email", "data_write", "env"]
TITLES = {
    "page": "Pages and screens", "route": "HTTP / RPC endpoints", "cli": "CLI commands",
    "mcp_tool": "AI-agent tools (MCP)", "job": "Jobs, workers, schedules", "webhook": "Webhooks",
    "outbound": "Outbound calls (check for user-supplied URLs: SSRF, data egress)",
    "email": "Email, SMS, push, auth links", "data_write": "Destructive writes (check: who may, is it audited)",
    "env": "Environment variables read",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    parser.add_argument("--out", help="write the result to this file")
    parser.add_argument("--include-tests", action="store_true", help="keep matches from test files")
    parser.add_argument("--runtime", help="local JSON route export (items list) or OpenAPI document; never fetched")
    args = parser.parse_args()
    root = os.path.abspath(args.project)
    if not os.path.isdir(root):
        sys.exit(f"Not a folder: {root}")
    diagnostics = []
    items = [i for i in scan(root, diagnostics) if args.include_tests or not i["test"]]
    if args.runtime:
        try:
            runtime = json.load(open(args.runtime, encoding="utf-8"))
            if "paths" in runtime:
                extra = [{"kind": "route", "what": method.upper() + " " + path, "where": "runtime:1", "test": False, "source": "runtime"}
                         for path, methods in runtime["paths"].items() for method in methods
                         if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options")]
            else:
                extra = runtime["items"]
            if not isinstance(extra, list) or any(not isinstance(i, dict) or not all(isinstance(i.get(k), str) for k in ("kind", "what", "where")) for i in extra):
                raise ValueError("runtime items require kind, what and where strings")
            items.extend({**i, "source": "runtime", "test": False} for i in extra)
        except (OSError, ValueError, KeyError, AttributeError, TypeError) as exc:
            parser.error(f"invalid runtime inventory: {exc}")
    if args.json:
        text = json.dumps({"version": 2, **identity(root), "items": items, "diagnostics": diagnostics,
                           "limits": "Heuristic inventory; reconcile skipped files, mounted/dynamic routes and runtime schemas before readiness."}, indent=2)
    else:
        out = [f"# Code inventory: {os.path.basename(root)}", "",
               "Heuristic map from `ct-inventory.py`. Starting point only: verify each entry, "
               "and look for kinds of surface this script does not know.", ""]
        counts = {k: sum(1 for i in items if i["kind"] == k) for k in ORDER}
        out.append("| Kind | Count |")
        out.append("|---|---|")
        out += [f"| {TITLES[k]} | {counts[k]} |" for k in ORDER]
        for kind in ORDER:
            rows = [i for i in items if i["kind"] == kind]
            if not rows:
                continue
            out += ["", f"## {TITLES[kind]} ({len(rows)})", ""]
            if kind == "env":
                names = sorted({i["what"] for i in rows})
                out.append(", ".join(f"`{n}`" for n in names))
                continue
            for i in sorted(rows, key=lambda r: (r["what"], r["where"]))[:400]:
                out.append(f"- `{i['what']}`  {i['where']}")
            if len(rows) > 400:
                out.append(f"- ... {len(rows) - 400} more (use --json for all)")
        out += ["", "## Scan limits requiring review"] + [f"- {d['path']}: {d['reason']}" for d in diagnostics]
        text = "\n".join(out) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Wrote {args.out}: {len(items)} items")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()

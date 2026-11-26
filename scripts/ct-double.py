#!/usr/bin/env python3
"""ct-double: a local stand-in for outside services, that records everything.

Point the product's service URL (an environment variable such as
RESEND_BASE_URL, OPENAI_BASE_URL, a webhook target or any API base URL) at
this server. It answers like the service would, and keeps every request so
tests can check exactly what the product sent: the email and its links,
the prompt and tool call, the webhook payload.

Usage:
    python3 ct-double.py --port 4010 --preset email --preset llm --preset webhook
    python3 ct-double.py --port 4011 --config double.yaml
    python3 ct-double.py --port 4443 --preset email --tls-cert cert.pem --tls-key key.pem

Presets:
    email    Resend (POST /emails), SendGrid (POST /v3/mail/send), Postmark
             (POST /email), Mailgun (POST /v3/<domain>/messages), SES v2
             (POST /v2/email/outbound-emails). Messages land in the inbox.
    llm      OpenAI-style POST /v1/chat/completions and Anthropic-style
             POST /v1/messages, with scripted replies or tool calls.
    webhook  Accepts any POST under /hooks/ and records it.

Config file (YAML or JSON) for any other service and for scripted replies:
    routes:
      - {method: GET, path: "/v1/accounts*", status: 200, json: {items: []}}
      - {method: POST, path: "/v1/messages/send", status: 201, json: {id: "m_1"}}
    llm:
      replies:
        - {match: "weather", reply: "It is sunny."}
        - {match: "delete", tool_call: {name: "delete_record", arguments: {id: 1}}}
      default: "OK (ct-double)"

Inspect from tests (JSON):
    GET    /_uf/requests[?path=<glob>]   everything received, newest last
    GET    /_uf/inbox[?to=<address>]     emails, with subject, text, html, links
    DELETE /_uf/requests                 clear requests and inbox

Unmatched requests get 404 {"error": "no ct-double route"} and are still
recorded, so you can see what the product tried to call. Authorization
headers are recorded as "<redacted>". Python 3 standard library only
(PyYAML only to read a YAML config).

Limits: a double proves the product calls the service correctly and copes
with its answers; it does not prove the real service behaves the same.
Streaming is supported for the OpenAI shape only (one chunk, then [DONE]).
"""
import argparse
import fnmatch
import json
import re
import ssl
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LOCK = threading.Lock()
REQUESTS = []
INBOX = []
CONFIG = {"routes": [], "llm": {}}
PRESETS = set()
RECORD = None
LINK = re.compile(r"https?://[^\s\"'<>)]+")


def links_in(*texts):
    found = []
    for text in texts:
        for link in LINK.findall(text or ""):
            link = link.rstrip(".,;")
            if link not in found:
                found.append(link)
    return found


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            out.append(item.get("email", "") if isinstance(item, dict) else str(item))
        return out
    if isinstance(value, dict):
        return [value.get("email", "")]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def add_mail(provider, sender, to, subject, text, html):
    message = {
        "id": f"msg_{uuid.uuid4().hex[:12]}", "provider": provider, "from": sender,
        "to": to, "subject": subject or "", "text": text or "", "html": html or "",
        "links": links_in(text, html), "received_at": time.time(),
    }
    with LOCK:
        INBOX.append(message)
    return message


def email_preset(method, path, body, form):
    if method != "POST":
        return None
    if path == "/emails":  # Resend
        m = add_mail("resend", body.get("from"), as_list(body.get("to")), body.get("subject"),
                     body.get("text"), body.get("html"))
        return 200, {"id": m["id"]}
    if path == "/v3/mail/send":  # SendGrid
        to = [t for p in body.get("personalizations", []) for t in as_list(p.get("to"))]
        content = {c.get("type"): c.get("value") for c in body.get("content", [])}
        add_mail("sendgrid", (body.get("from") or {}).get("email"), to, body.get("subject"),
                 content.get("text/plain"), content.get("text/html"))
        return 202, {}
    if path == "/email":  # Postmark
        m = add_mail("postmark", body.get("From"), as_list(body.get("To")), body.get("Subject"),
                     body.get("TextBody"), body.get("HtmlBody"))
        return 200, {"MessageID": m["id"], "ErrorCode": 0, "Message": "OK"}
    if re.fullmatch(r"/v3/[^/]+/messages", path):  # Mailgun (form fields)
        get = lambda k: (form.get(k) or [""])[0]
        m = add_mail("mailgun", get("from"), as_list(get("to")), get("subject"), get("text"), get("html"))
        return 200, {"id": f"<{m['id']}@ct-double>", "message": "Queued. Thank you."}
    if path == "/v2/email/outbound-emails":  # SES v2
        dest = body.get("Destination", {})
        simple = (body.get("Content", {}) or {}).get("Simple", {})
        m = add_mail("ses", body.get("FromEmailAddress"), as_list(dest.get("ToAddresses")),
                     (simple.get("Subject") or {}).get("Data"),
                     ((simple.get("Body") or {}).get("Text") or {}).get("Data"),
                     ((simple.get("Body") or {}).get("Html") or {}).get("Data"))
        return 200, {"MessageId": m["id"]}
    return None


def llm_reply(prompt_text):
    cfg = CONFIG.get("llm") or {}
    for rule in cfg.get("replies", []):
        if re.search(rule.get("match", "$^"), prompt_text, re.I):
            return rule
    return {"reply": cfg.get("default", "OK (ct-double)")}


def llm_preset(method, path, body):
    if method != "POST":
        return None
    if path.endswith("/chat/completions"):  # OpenAI shape
        prompt = json.dumps(body.get("messages", []))
        rule = llm_reply(prompt)
        message = {"role": "assistant", "content": rule.get("reply")}
        finish = "stop"
        if rule.get("tool_call"):
            call = rule["tool_call"]
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": f"call_{uuid.uuid4().hex[:8]}", "type": "function",
                "function": {"name": call.get("name"), "arguments": json.dumps(call.get("arguments", {}))}}]}
            finish = "tool_calls"
        result = {"id": f"chatcmpl-{uuid.uuid4().hex[:10]}", "object": "chat.completion",
                  "model": body.get("model", "ct-double"), "created": int(time.time()),
                  "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                  "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        if body.get("stream"):
            chunk = {"id": result["id"], "object": "chat.completion.chunk", "model": result["model"],
                     "choices": [{"index": 0, "delta": message, "finish_reason": finish}]}
            return 200, f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n", "text/event-stream"
        return 200, result
    if path.endswith("/messages") and "anthropic-version" in (CURRENT.headers or {}):  # Anthropic shape
        prompt = json.dumps(body.get("messages", []))
        rule = llm_reply(prompt)
        if rule.get("tool_call"):
            call = rule["tool_call"]
            content = [{"type": "tool_use", "id": f"toolu_{uuid.uuid4().hex[:10]}",
                        "name": call.get("name"), "input": call.get("arguments", {})}]
            stop = "tool_use"
        else:
            content = [{"type": "text", "text": rule.get("reply")}]
            stop = "end_turn"
        return 200, {"id": f"msg_{uuid.uuid4().hex[:12]}", "type": "message", "role": "assistant",
                     "model": body.get("model", "ct-double"), "content": content,
                     "stop_reason": stop, "usage": {"input_tokens": 1, "output_tokens": 1}}
    return None


class _Current(threading.local):
    headers = None


CURRENT = _Current()


class Handler(BaseHTTPRequestHandler):
    server_version = "ct-double/1"

    def log_message(self, fmt, *args):  # quiet; everything is in /_uf/requests
        pass

    def _send(self, status, payload, content_type="application/json"):
        data = payload if isinstance(payload, (bytes, str)) else json.dumps(payload)
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin") or "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.end_headers()
        self.wfile.write(data)

    def _handle(self):
        url = urlparse(self.path)
        path, query = url.path, parse_qs(url.query)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        text = raw.decode("utf-8", errors="replace")
        body, form = {}, {}
        ctype = self.headers.get("Content-Type", "")
        if "json" in ctype or text.strip().startswith(("{", "[")):
            try:
                body = json.loads(text) if text else {}
            except ValueError:
                body = {}
        elif "form" in ctype:
            form = parse_qs(text)
        CURRENT.headers = {k.lower(): v for k, v in self.headers.items()}

        if path.startswith("/_uf/"):
            return self._introspect(path, query)
        if self.command == "OPTIONS":
            return self._send(204, b"")

        headers = {k: ("<redacted>" if k.lower() in ("authorization", "x-api-key", "cookie") else v)
                   for k, v in self.headers.items()}
        entry = {"time": time.time(), "method": self.command, "path": path,
                 "query": {k: v[0] if len(v) == 1 else v for k, v in query.items()},
                 "headers": headers, "body": body if body else (form or text)}
        answer = None
        if "email" in PRESETS:
            answer = email_preset(self.command, path, body if isinstance(body, dict) else {}, form)
        if answer is None and "llm" in PRESETS:
            answer = llm_preset(self.command, path, body if isinstance(body, dict) else {})
        if answer is None and "webhook" in PRESETS and path.startswith("/hooks/") and self.command == "POST":
            answer = (200, {"ok": True})
        if answer is None:
            for route in CONFIG.get("routes", []):
                if route.get("method", "GET").upper() in (self.command, "ANY") and \
                        fnmatch.fnmatchcase(path, route.get("path", "")):
                    payload = route.get("json") if "json" in route else route.get("body", "")
                    answer = (int(route.get("status", 200)), payload,
                              "application/json" if "json" in route else route.get("content_type", "text/plain"))
                    break
        if answer is None:
            answer = (404, {"error": "no ct-double route", "method": self.command, "path": path})
        entry["status"] = answer[0]
        with LOCK:
            REQUESTS.append(entry)
            if RECORD:
                with open(RECORD, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry) + "\n")
        self._send(*answer)

    def _introspect(self, path, query):
        if path == "/_uf/requests" and self.command == "DELETE":
            with LOCK:
                REQUESTS.clear()
                INBOX.clear()
            return self._send(200, {"cleared": True})
        if path == "/_uf/requests":
            pattern = (query.get("path") or ["*"])[0]
            with LOCK:
                items = [r for r in REQUESTS if fnmatch.fnmatchcase(r["path"], pattern)]
            return self._send(200, items)
        if path == "/_uf/inbox":
            to = (query.get("to") or [None])[0]
            with LOCK:
                items = [m for m in INBOX if not to or any(to.lower() == t.lower() for t in m["to"])]
            return self._send(200, items)
        if path == "/_uf/health":
            return self._send(200, {"ok": True, "presets": sorted(PRESETS), "routes": len(CONFIG["routes"])})
        return self._send(404, {"error": "unknown /_uf endpoint"})

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _handle


def main():
    global RECORD
    parser = argparse.ArgumentParser(description="Local stand-in for outside services that records everything.")
    parser.add_argument("--port", type=int, default=4010)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--preset", action="append", choices=["email", "llm", "webhook"], default=[])
    parser.add_argument("--config", help="YAML or JSON file with routes and llm replies")
    parser.add_argument("--record", help="also append every request to this JSONL file")
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    args = parser.parse_args()
    PRESETS.update(args.preset)
    RECORD = args.record
    if args.config:
        with open(args.config, encoding="utf-8") as handle:
            text = handle.read()
        if args.config.endswith((".yaml", ".yml")):
            try:
                import yaml
            except ImportError:
                sys.exit("Reading a YAML config needs PyYAML (pip install pyyaml), or use JSON.")
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)
        CONFIG["routes"] = data.get("routes", [])
        CONFIG["llm"] = data.get("llm", {})
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    scheme = "http"
    if args.tls_cert and args.tls_key:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.tls_cert, args.tls_key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"
    print(f"ct-double on {scheme}://{args.host}:{args.port} presets={sorted(PRESETS) or 'none'} "
          f"routes={len(CONFIG['routes'])}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

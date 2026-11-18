"""Tests for scripts/uf-double.py: the stand-in for outside services."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "uf-double.py")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class DoubleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        config = os.path.join(cls.tmp.name, "double.json")
        with open(config, "w") as handle:
            json.dump({"routes": [{"method": "GET", "path": "/v1/accounts*", "status": 200, "json": {"items": [1]}}],
                       "llm": {"replies": [{"match": "delete", "tool_call": {"name": "delete_record", "arguments": {"id": 7}}}],
                               "default": "hello"}}, handle)
        cls.port = free_port()
        cls.proc = subprocess.Popen([sys.executable, SCRIPT, "--port", str(cls.port), "--preset", "email",
                                     "--preset", "llm", "--preset", "webhook", "--config", config],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(50):
            try:
                urllib.request.urlopen(cls.base + "/_uf/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=5)
        cls.tmp.cleanup()

    def call(self, method, path, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    def test_email_is_caught_with_links(self):
        self.call("POST", "/emails", {"from": "app@x.test", "to": ["ann@inbox.test"], "subject": "Invite",
                                      "html": '<a href="https://app.test/accept?token=t1">Join</a>'},
                  {"Authorization": "Bearer secret"})
        status, inbox = self.call("GET", "/_uf/inbox?to=ann@inbox.test")
        self.assertEqual(status, 200)
        self.assertEqual(inbox[0]["subject"], "Invite")
        self.assertEqual(inbox[0]["links"], ["https://app.test/accept?token=t1"])
        status, requests = self.call("GET", "/_uf/requests?path=/emails")
        self.assertEqual(requests[0]["headers"].get("Authorization"), "<redacted>")

    def test_llm_reply_and_tool_call(self):
        status, body = self.call("POST", "/v1/chat/completions", {"model": "m", "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(body["choices"][0]["message"]["content"], "hello")
        status, body = self.call("POST", "/v1/chat/completions", {"model": "m", "messages": [{"role": "user", "content": "delete it"}]})
        self.assertEqual(body["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(body["choices"][0]["message"]["tool_calls"][0]["function"]["name"], "delete_record")
        status, body = self.call("POST", "/v1/messages", {"model": "m", "messages": [{"role": "user", "content": "delete"}]},
                                 {"anthropic-version": "2023-06-01"})
        self.assertEqual(body["stop_reason"], "tool_use")

    def test_webhook_custom_route_and_unmatched(self):
        self.call("POST", "/hooks/crm", {"event": "person.created", "email": "erased@x.test"})
        status, requests = self.call("GET", "/_uf/requests?path=/hooks/*")
        self.assertEqual(requests[-1]["body"]["email"], "erased@x.test")
        status, body = self.call("GET", "/v1/accounts?x=1")
        self.assertEqual((status, body), (200, {"items": [1]}))
        status, body = self.call("GET", "/v2/unknown")
        self.assertEqual(status, 404)
        status, requests = self.call("GET", "/_uf/requests?path=/v2/unknown")
        self.assertEqual(len(requests), 1)


if __name__ == "__main__":
    unittest.main()

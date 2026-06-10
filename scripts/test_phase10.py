"""Phase 10 full test suite — run with: uv run python scripts/test_phase10.py"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8001/api/v1"


def post_json(path: str, body: dict, timeout: int = 120) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_json(path: str) -> dict | list:
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


TESTS = [
    {
        "label": "UBO disclosure clause (articles of association)",
        "body": {
            "request": "Draft a UBO beneficial ownership disclosure clause for an ADGM private company.",
            "document_type": "articles_of_association",
            "top_k": 8,
        },
    },
    {
        "label": "Employment probation clause",
        "body": {
            "request": "Generate an employment probation period clause compliant with ADGM employment regulations.",
            "document_type": "employment_contract",
            "top_k": 8,
        },
    },
    {
        "label": "Via chat intent router (clause_generation path)",
        "endpoint": "/chat",
        "body": {
            "question": "Draft a share transfer restriction clause for an ADGM private company articles of association.",
            "top_k": 8,
        },
    },
]

all_passed = True

for t in TESTS:
    endpoint = t.get("endpoint", "/generated-clauses/generate")
    key = "answer" if endpoint == "/chat" else "clause_text"
    print(f"\n{'='*68}")
    print(f"TEST: {t['label']}")
    print(f"{'='*68}")
    try:
        data = post_json(endpoint, t["body"], timeout=180)
        model   = data.get("model", "?")
        latency = data.get("latency_ms", "?")
        text    = data.get(key, "")
        cites   = data.get("citations", data.get("sources", []))
        print(f"Model    : {model}")
        print(f"Latency  : {latency} ms")
        print(f"Citations: {len(cites)}")
        print(f"Clause   :\n{text[:600]}")
        if not text:
            print("FAIL — empty clause text")
            all_passed = False
        else:
            print("PASS")
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()[:300]}")
        all_passed = False
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        all_passed = False

# CRUD still works
print(f"\n{'='*68}")
print("TEST: GET /generated-clauses (CRUD intact)")
print(f"{'='*68}")
try:
    records = get_json("/generated-clauses")
    print(f"Records in DB: {len(records)}  PASS")
except Exception as exc:
    print(f"FAIL: {exc}")
    all_passed = False

print(f"\n{'='*68}")
print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
print(f"{'='*68}")
sys.exit(0 if all_passed else 1)

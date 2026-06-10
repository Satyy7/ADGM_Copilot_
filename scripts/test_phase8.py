"""Phase 8 end-to-end validation — run with: uv run python scripts/test_phase8.py"""

import json
import urllib.request

URL = "http://localhost:8001/api/v1/chat"

QUERIES = [
    {
        "label": "compliance_chat (route -> retrieve -> generate)",
        "body": {"question": "What are the UBO beneficial ownership requirements under ADGM?", "top_k": 5},
    },
    {
        "label": "compliance_review stub (Phase 9)",
        "body": {"question": "Please review my company's Articles of Association for ADGM compliance.", "top_k": 5},
    },
    {
        "label": "clause_generation stub (Phase 10)",
        "body": {"question": "Draft a UBO disclosure clause for an ADGM private company.", "top_k": 5},
    },
    {
        "label": "analytics stub (Phase 12)",
        "body": {"question": "How many compliance violations were recorded last quarter?", "top_k": 5},
    },
]


def post(body: dict) -> dict:
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        URL, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


for q in QUERIES:
    print(f"\n{'='*70}")
    print(f"TEST: {q['label']}")
    print(f"{'='*70}")
    try:
        data = post(q["body"])
        print(f"Model    : {data['model']}")
        print(f"Latency  : {data['latency_ms']} ms")
        print(f"Chunks   : {data['chunks_used']}")
        print(f"Answer   : {data['answer'][:300]}")
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()[:300]}")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")

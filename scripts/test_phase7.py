"""Phase 7 end-to-end validation — run with: uv run python scripts/test_phase7.py"""

import json
import urllib.request

QUESTION = "What are the UBO beneficial ownership disclosure requirements under ADGM regulations?"
URL = "http://localhost:8001/api/v1/chat"

payload = json.dumps({"question": QUESTION, "top_k": 5}).encode()
req = urllib.request.Request(
    URL,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())

    print(f"Model     : {data['model']}")
    print(f"Latency   : {data['latency_ms']} ms")
    print(f"Chunks    : {data['chunks_used']}")
    print()
    print("--- Retrieved chunks (re-ranked scores) ---")
    for i, c in enumerate(data["retrieved_chunks"], 1):
        print(f"  #{i} [{c['score']:.5f}] [{c['collection']}] {c['text'][:90]}")
    print()
    print("--- Answer (first 700 chars) ---")
    print(data["answer"][:700])

except urllib.error.HTTPError as exc:
    body = exc.read().decode()
    print(f"HTTP {exc.code}: {body}")
except Exception as exc:
    print(f"ERROR: {type(exc).__name__}: {exc}")

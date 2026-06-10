"""Verify all review routes still work after Phase 9 changes."""
import json
import urllib.request

BASE = "http://localhost:8001/api/v1"

# 1. GET /reviews — CRUD list still works
req = urllib.request.Request(f"{BASE}/reviews", method="GET")
with urllib.request.urlopen(req, timeout=10) as r:
    records = json.loads(r.read())
print(f"GET /reviews OK — {len(records)} records")

# 2. OpenAPI schema includes /analyze endpoint
req = urllib.request.Request(f"{BASE.replace('/api/v1','')}/openapi.json", method="GET")
with urllib.request.urlopen(req, timeout=10) as r:
    schema = json.loads(r.read())
paths = list(schema["paths"].keys())
analyze_path = "/api/v1/reviews/analyze"
assert analyze_path in paths, f"{analyze_path} not in OpenAPI schema"
print(f"OpenAPI /analyze endpoint registered: {analyze_path}")
print("All route checks passed.")

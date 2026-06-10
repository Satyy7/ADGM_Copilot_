"""Phase 9 end-to-end test — run with: uv run python scripts/test_phase9_e2e.py"""

import json
import urllib.request
import urllib.parse
import sys

# Use one of the real ADGM template DOCX files already in the repo
DOCX_PATH = "data/raw/templates/551f3e35d06100ef.docx"
URL = "http://localhost:8001/api/v1/reviews/analyze"

BOUNDARY = "----FormBoundaryPhase9Test"


def build_multipart(filepath: str, boundary: str) -> tuple[bytes, str]:
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    filename = filepath.split("/")[-1].split("\\")[-1]

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n"
        f"\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


body, content_type = build_multipart(DOCX_PATH, BOUNDARY)
req = urllib.request.Request(
    URL,
    data=body,
    headers={"Content-Type": content_type},
    method="POST",
)

print(f"Uploading: {DOCX_PATH}")
print(f"Endpoint:  {URL}\n")

try:
    with urllib.request.urlopen(req, timeout=240) as resp:
        data = json.loads(resp.read())

    print(f"Document type   : {data['document_type']}")
    print(f"Compliance score: {data['compliance_score']}/100")
    print(f"Violations      : {len(data['violations'])}")
    print(f"Gaps            : {len(data['gaps'])}")
    print(f"Total issues    : {data['total_issues']}")
    print(f"Model           : {data['model']}")
    print(f"Latency         : {data['latency_ms']} ms")
    print()
    print("--- Summary ---")
    print(data["summary"][:500])
    print()
    if data["violations"]:
        print("--- Top violation ---")
        v = data["violations"][0]
        print(f"  [{v['severity'].upper()}] {v['title']}")
        print(f"  Clause   : {v['clause_heading']}")
        print(f"  Reg ref  : {v.get('regulation_reference', 'n/a')}")
        print(f"  Fix      : {v['recommendation'][:150]}")
    if data["gaps"]:
        print()
        print("--- Top gap ---")
        g = data["gaps"][0]
        print(f"  [{g['severity'].upper()}] {g['missing_provision']}")
        print(f"  Fix: {g['recommendation'][:150]}")

except urllib.error.HTTPError as exc:
    print(f"HTTP {exc.code}: {exc.read().decode()[:500]}")
    sys.exit(1)
except Exception as exc:
    print(f"ERROR: {type(exc).__name__}: {exc}")
    sys.exit(1)

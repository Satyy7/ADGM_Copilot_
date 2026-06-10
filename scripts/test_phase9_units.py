"""Phase 9 unit tests — run with: uv run python scripts/test_phase9_units.py"""

from backend.app.schemas.review_report import ReviewReport, DetectedViolation, IdentifiedGap
from backend.app.services.document_extractor import extract_text, _MAX_CHARS
from backend.app.agent.review.prompts import CLASSIFY_PROMPT, EXTRACT_CLAUSES_PROMPT
from backend.app.agent.review.nodes import _parse_json_array, _calculate_score
from backend.app.agent.review.graph import ReviewState

# JSON parser
assert _parse_json_array('[{"a":1},{"b":2}]') == [{"a": 1}, {"b": 2}], "direct parse"
assert _parse_json_array('text [{"a":1}] more') == [{"a": 1}], "embedded parse"
assert _parse_json_array("no json here") == [], "fallback to empty"
print("_parse_json_array OK")

# Score calculator
assert _calculate_score([], []) == 100.0
assert _calculate_score([{"severity": "high"}, {"severity": "medium"}], []) == 78.0
assert _calculate_score([], [{"severity": "high"}]) == 90.0
assert _calculate_score([{"severity": "high"}] * 7, []) == 0.0  # floor
print("_calculate_score OK")

# Schema coercion
v = DetectedViolation(
    clause_heading="Article 3",
    clause_excerpt="The share capital...",
    violation_type="non_compliant_clause",
    severity="high",
    title="Missing UBO disclosure",
    description="ADGM requires...",
    regulation_reference="Article 15",
    recommendation="Add a UBO clause.",
)
assert v.severity == "high"
print("DetectedViolation schema OK")

g = IdentifiedGap(
    missing_provision="Register of members",
    severity="medium",
    regulation_reference="Section 12",
    recommendation="Add a register of members clause.",
)
assert g.severity == "medium"
print("IdentifiedGap schema OK")

# Constants
assert _MAX_CHARS == 8000
print("document_extractor constants OK")

print("\nAll Phase 9 unit checks passed.")

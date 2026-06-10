"""Seed synthetic historical reviews into the Qdrant historical_reviews collection.

Run with:
    uv run python scripts/seed_historical_reviews.py

This populates the collection with realistic ADGM compliance scenarios so
the Phase 11 similarity search returns meaningful results during testing.
The seed is idempotent -- re-running upserts the same point IDs.
"""

import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, ".")

from backend.app.agent.cases.indexer import HistoricalReviewIndexer
from backend.app.core.config import get_settings
from backend.app.db.qdrant import get_qdrant_client
from backend.app.schemas.case_result import SimilarCase
from backend.app.schemas.review_report import (
    DetectedViolation,
    IdentifiedGap,
    ReviewReport,
)
from backend.app.services.embeddings import get_embeddings_service

# ---------------------------------------------------------------------------
# Synthetic historical review records
# ---------------------------------------------------------------------------

SEED_REVIEWS: list[ReviewReport] = [
    ReviewReport(
        document_name="alpha_corp_articles_of_association_v2.pdf",
        document_type="articles_of_association",
        compliance_score=62.0,
        summary=(
            "Alpha Corp's Articles of Association contains several material non-compliances "
            "with ADGM Companies Regulations 2020. The UBO disclosure provisions are absent, "
            "share transfer restrictions do not meet the required formality, and the quorum "
            "requirements for extraordinary resolutions are below the statutory minimum. "
            "Immediate remediation is recommended before the company commences operations."
        ),
        violations=[
            DetectedViolation(
                clause_heading="Article 15 - Share Transfer",
                clause_excerpt="Shares may be transferred subject to board approval.",
                violation_type="inadequate_provision",
                severity="high",
                title="Share transfer restrictions below statutory minimum",
                description=(
                    "ADGM Companies Regulations 2020 require share transfer restrictions "
                    "to include pre-emption rights and drag-along provisions for private companies."
                ),
                regulation_reference="ADGM Companies Regulations 2020, Section 94",
                recommendation="Add pre-emption rights clause and drag-along/tag-along provisions.",
            ),
            DetectedViolation(
                clause_heading="Article 22 - Quorum",
                clause_excerpt="A quorum shall consist of two members present in person.",
                violation_type="non_compliant_clause",
                severity="medium",
                title="Quorum for extraordinary resolutions insufficient",
                description=(
                    "Special resolutions require a qualified majority. The two-member quorum "
                    "fails to meet the 75% voting threshold requirement."
                ),
                regulation_reference="ADGM Companies Regulations 2020, Section 182",
                recommendation="Revise quorum clauses to specify 75% threshold for special resolutions.",
            ),
        ],
        gaps=[
            IdentifiedGap(
                missing_provision="Beneficial ownership (UBO) disclosure obligations",
                severity="high",
                regulation_reference="ADGM Beneficial Ownership Regulations 2018",
                recommendation="Insert mandatory UBO disclosure and register maintenance clauses.",
            ),
            IdentifiedGap(
                missing_provision="Annual general meeting (AGM) requirement",
                severity="medium",
                regulation_reference="ADGM Companies Regulations 2020, Section 175",
                recommendation="Add AGM obligation clause with 15-month maximum interval.",
            ),
        ],
        total_issues=4,
        model="gemini-2.0-flash",
        latency_ms=8420.0,
        similar_cases=[],
    ),

    ReviewReport(
        document_name="beta_tech_employment_contract_senior_dev.docx",
        document_type="employment_contract",
        compliance_score=74.0,
        summary=(
            "Beta Tech's senior developer employment contract is partially compliant with "
            "ADGM Employment Regulations 2019. The probation period exceeds the permitted "
            "six-month maximum, and the termination notice periods do not match the statutory "
            "schedule based on length of service. The non-compete clause geographic scope is "
            "overly broad and likely unenforceable. Core entitlements including annual leave "
            "and end-of-service gratuity are correctly stated."
        ),
        violations=[
            DetectedViolation(
                clause_heading="Clause 4 - Probationary Period",
                clause_excerpt="The probationary period shall be twelve (12) months from the commencement date.",
                violation_type="non_compliant_clause",
                severity="high",
                title="Probation period exceeds statutory maximum",
                description=(
                    "ADGM Employment Regulations 2019 cap the probationary period at six months. "
                    "A twelve-month probation is void under ADGM law."
                ),
                regulation_reference="ADGM Employment Regulations 2019, Article 28",
                recommendation="Reduce probation period to maximum six months.",
            ),
            DetectedViolation(
                clause_heading="Clause 18 - Non-Compete",
                clause_excerpt="Employee shall not compete globally for 3 years after termination.",
                violation_type="prohibited_term",
                severity="medium",
                title="Non-compete clause is unreasonably broad",
                description=(
                    "A global three-year non-compete is disproportionate and unenforceable. "
                    "ADGM courts apply reasonableness tests on geographic and temporal scope."
                ),
                regulation_reference="ADGM Employment Regulations 2019, Article 68",
                recommendation="Restrict non-compete to 12 months and relevant geographic markets.",
            ),
        ],
        gaps=[
            IdentifiedGap(
                missing_provision="End-of-service gratuity calculation method",
                severity="medium",
                regulation_reference="ADGM Employment Regulations 2019, Article 56",
                recommendation="Include explicit gratuity calculation formula (21 days per year for first 5 years).",
            ),
        ],
        total_issues=3,
        model="gemini-2.0-flash",
        latency_ms=7890.0,
        similar_cases=[],
    ),

    ReviewReport(
        document_name="gamma_holdings_memorandum_of_association.pdf",
        document_type="memorandum_of_association",
        compliance_score=55.0,
        summary=(
            "Gamma Holdings' Memorandum of Association has critical structural deficiencies. "
            "The stated objects clause is impermissibly narrow, the share capital structure "
            "does not distinguish between authorised and issued capital, and the liability "
            "clause is absent. Several mandatory statements required by the ADGM Companies "
            "Regulations 2020 are missing from the instrument."
        ),
        violations=[
            DetectedViolation(
                clause_heading="Clause 3 - Objects",
                clause_excerpt="The company is incorporated to conduct financial services activities.",
                violation_type="inadequate_provision",
                severity="high",
                title="Objects clause insufficient for ADGM financial services licensing",
                description=(
                    "FSRA-regulated entities require specific regulatory activity categories in the "
                    "objects clause aligned with their Financial Services Permission (FSP)."
                ),
                regulation_reference="ADGM Financial Services and Markets Regulations 2015, Section 14",
                recommendation="Specify authorised financial services activities as defined in the FSP application.",
            ),
            DetectedViolation(
                clause_heading="Clause 5 - Share Capital",
                clause_excerpt="The company has share capital of USD 50,000.",
                violation_type="missing_disclosure",
                severity="medium",
                title="Share capital statement lacks required detail",
                description=(
                    "The MoA must state the authorised share capital, number of shares, "
                    "par value per share, and classes of shares with rights attached."
                ),
                regulation_reference="ADGM Companies Regulations 2020, Section 8",
                recommendation="Restate share capital with full class rights, par value, and authorised/issued split.",
            ),
        ],
        gaps=[
            IdentifiedGap(
                missing_provision="Member liability limitation clause",
                severity="high",
                regulation_reference="ADGM Companies Regulations 2020, Section 9",
                recommendation="Insert statutory liability limitation statement for limited liability company.",
            ),
            IdentifiedGap(
                missing_provision="Registered office address in ADGM",
                severity="high",
                regulation_reference="ADGM Companies Regulations 2020, Section 86",
                recommendation="State the registered office address within ADGM jurisdiction.",
            ),
            IdentifiedGap(
                missing_provision="Company type declaration (private/public)",
                severity="medium",
                regulation_reference="ADGM Companies Regulations 2020, Section 4",
                recommendation="Explicitly state the company type as private company limited by shares.",
            ),
        ],
        total_issues=5,
        model="gemini-2.0-flash",
        latency_ms=9150.0,
        similar_cases=[],
    ),

    ReviewReport(
        document_name="delta_fund_board_resolution_2024_q4.docx",
        document_type="board_resolution",
        compliance_score=81.0,
        summary=(
            "Delta Fund Management's Q4 2024 board resolution is largely compliant with "
            "ADGM governance requirements. The resolution is properly executed with requisite "
            "director signatures and board quorum achieved. Minor issues include insufficient "
            "conflict-of-interest disclosure by one director and the absence of a minute secretary "
            "attestation. The investment decision covered by the resolution falls within the "
            "company's stated investment policy."
        ),
        violations=[
            DetectedViolation(
                clause_heading="Section 3 - Conflict of Interest",
                clause_excerpt="All directors confirm no conflict of interest in the proposed transaction.",
                violation_type="missing_disclosure",
                severity="medium",
                title="Blanket conflict declaration insufficient",
                description=(
                    "Director Ahmed Al-Rashid holds a 15% interest in the counterparty entity. "
                    "A blanket declaration does not satisfy the material interest disclosure "
                    "obligation under ADGM Companies Regulations 2020."
                ),
                regulation_reference="ADGM Companies Regulations 2020, Section 165",
                recommendation="Require individual conflict-of-interest declarations identifying material interests.",
            ),
        ],
        gaps=[
            IdentifiedGap(
                missing_provision="Minute secretary attestation",
                severity="low",
                regulation_reference="ADGM Companies Regulations 2020, Section 248",
                recommendation="Include minute secretary signature to certify accuracy of the board minutes.",
            ),
        ],
        total_issues=2,
        model="gemini-2.0-flash",
        latency_ms=5340.0,
        similar_cases=[],
    ),

    ReviewReport(
        document_name="epsilon_ventures_shareholder_resolution_ubo.docx",
        document_type="shareholder_resolution",
        compliance_score=100.0,
        summary=(
            "Epsilon Ventures' shareholder resolution for UBO register update is fully "
            "compliant with all applicable ADGM regulations. The resolution correctly "
            "identifies the beneficial owners, specifies their ownership percentages, "
            "includes required passport and address details, and follows the required "
            "special resolution procedure with 75% majority. No violations or gaps identified."
        ),
        violations=[],
        gaps=[],
        total_issues=0,
        model="gemini-2.0-flash",
        latency_ms=4220.0,
        similar_cases=[],
    ),
]


def main() -> None:
    print("=" * 65)
    print("Phase 11 — Seeding historical_reviews Qdrant collection")
    print("=" * 65)

    settings   = get_settings()
    qdrant     = get_qdrant_client()
    embeddings = get_embeddings_service(settings=settings)
    indexer    = HistoricalReviewIndexer(qdrant=qdrant, embeddings=embeddings)

    success = 0
    for review in SEED_REVIEWS:
        print(f"\nIndexing: {review.document_name}")
        print(f"  Type    : {review.document_type}")
        print(f"  Score   : {review.compliance_score}/100")
        print(f"  Issues  : {review.total_issues}")
        point_id = indexer.index(review)
        if point_id:
            print(f"  Point ID: {point_id}  OK")
            success += 1
        else:
            print("  FAILED to index (check logs)")

    print(f"\n{'=' * 65}")
    print(f"Seeded {success}/{len(SEED_REVIEWS)} historical reviews.")
    if success == len(SEED_REVIEWS):
        print("All reviews indexed successfully. Phase 11 search is ready.")
    else:
        print("Some reviews failed to index. Check Qdrant connectivity and API keys.")
    print("=" * 65)
    sys.exit(0 if success == len(SEED_REVIEWS) else 1)


if __name__ == "__main__":
    main()

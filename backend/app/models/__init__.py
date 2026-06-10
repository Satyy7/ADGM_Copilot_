"""ORM models for ADGM Compliance Copilot.

Importing this package registers all model metadata with SQLAlchemy. The local
database initializer and future migration tooling depend on these imports.
"""

from backend.app.models.audit_log import AuditLog
from backend.app.models.document import Document
from backend.app.models.generated_clause import GeneratedClause
from backend.app.models.query_log import QueryLog
from backend.app.models.recommendation import Recommendation
from backend.app.models.review import Review
from backend.app.models.user import User
from backend.app.models.violation import Violation

__all__ = [
    "AuditLog",
    "Document",
    "GeneratedClause",
    "QueryLog",
    "Recommendation",
    "Review",
    "User",
    "Violation",
]


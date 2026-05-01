"""
Pydantic Output Schemas
========================
Defines the structured output format that LangChain's GPT-4o-mini
must return for every analyzed email. Using Pydantic v2 models ensures
type safety, validation, and seamless integration with LangChain's
`with_structured_output()` method.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ImportanceLevel(str, Enum):
    """Classification tiers for email importance."""

    CRITICAL = "CRITICAL"   # Requires immediate action (deadlines, urgent requests)
    HIGH = "HIGH"           # Important but not time-sensitive
    MEDIUM = "MEDIUM"       # Useful information, can be reviewed later
    LOW = "LOW"             # Informational, no action needed
    JUNK = "JUNK"           # Promotions, newsletters, spam — should be filtered


class EmailCategory(str, Enum):
    """High-level categorization of the email's purpose."""

    WORK = "WORK"
    PERSONAL = "PERSONAL"
    FINANCE = "FINANCE"
    MEETING = "MEETING"
    DEADLINE = "DEADLINE"
    SUPPORT = "SUPPORT"
    NEWSLETTER = "NEWSLETTER"
    PROMOTION = "PROMOTION"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"


class EmailAnalysis(BaseModel):
    """
    Structured output schema for the AI email analysis chain.

    Every email processed by the LLM is transformed into this
    validated format before being sent to Telegram or logged.
    """

    # ── Classification ───────────────────────────────────────────
    importance: ImportanceLevel = Field(
        description=(
            "The importance level of this email. Use CRITICAL for urgent "
            "deadlines or action-required items, HIGH for important business "
            "communications, MEDIUM for useful but non-urgent info, LOW for "
            "informational content, and JUNK for promotions/spam/newsletters."
        )
    )
    category: EmailCategory = Field(
        description=(
            "The primary category this email falls into, such as WORK, "
            "PERSONAL, FINANCE, MEETING, DEADLINE, PROMOTION, etc."
        )
    )
    is_junk: bool = Field(
        description=(
            "True if the email is a promotion, newsletter, marketing material, "
            "automated notification with no actionable content, or spam. "
            "False for any email that contains meaningful, human-written content."
        )
    )

    # ── Extracted Content ────────────────────────────────────────
    sender_name: str = Field(
        description="The human-readable name of the sender (e.g., 'Alice Johnson')."
    )
    sender_email: str = Field(
        description="The sender's email address (e.g., 'alice@example.com')."
    )
    summary: str = Field(
        description=(
            "A concise 1-3 sentence summary of the email's core message. "
            "Focus on what the sender wants, any requests, or key information. "
            "Do NOT include greetings or sign-offs."
        )
    )
    action_required: bool = Field(
        description=(
            "True if the email explicitly or implicitly asks the recipient "
            "to do something (reply, review, approve, attend, etc.)."
        )
    )
    deadline: Optional[str] = Field(
        default=None,
        description=(
            "Any deadline, due date, or time-sensitive date mentioned in the "
            "email. Use the format found in the email (e.g., 'May 5, 2026', "
            "'end of week', 'ASAP'). Set to null if no deadline is mentioned."
        )
    )
    key_points: list[str] = Field(
        default_factory=list,
        description=(
            "A list of 1-4 bullet-point key takeaways or action items "
            "extracted from the email. Keep each point brief and actionable."
        )
    )

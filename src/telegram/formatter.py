"""
Telegram Message Formatter
============================
Transforms an EmailAnalysis Pydantic object into a beautifully
formatted Telegram Markdown (MarkdownV2) message.

Telegram MarkdownV2 requires escaping special characters:
  _ * [ ] ( ) ~ ` > # + - = | { } . !

This module handles all escaping automatically.
"""

from src.ai.schemas import EmailAnalysis, ImportanceLevel


# ── Emoji Maps ───────────────────────────────────────────────────

IMPORTANCE_EMOJI = {
    ImportanceLevel.CRITICAL: "🔴",
    ImportanceLevel.HIGH: "🟠",
    ImportanceLevel.MEDIUM: "🟡",
    ImportanceLevel.LOW: "🟢",
    ImportanceLevel.JUNK: "⚪",
}

IMPORTANCE_LABEL = {
    ImportanceLevel.CRITICAL: "CRITICAL",
    ImportanceLevel.HIGH: "HIGH",
    ImportanceLevel.MEDIUM: "MEDIUM",
    ImportanceLevel.LOW: "LOW",
    ImportanceLevel.JUNK: "JUNK",
}

# Characters that must be escaped in Telegram MarkdownV2
_ESCAPE_CHARS = r"\_*[]()~`>#+-=|{}.!"


def _escape_md(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2 format.

    Args:
        text: Raw text string.

    Returns:
        The escaped string safe for MarkdownV2 parsing.
    """
    result = []
    for char in text:
        if char in _ESCAPE_CHARS:
            result.append(f"\\{char}")
        else:
            result.append(char)
    return "".join(result)


def format_email_notification(
    analysis: EmailAnalysis,
    subject: str,
) -> str:
    """
    Format an EmailAnalysis into an elegant Telegram MarkdownV2 message.

    Produces a visually structured notification with:
      - Importance badge with color-coded emoji
      - Sender info and subject line
      - AI-generated summary
      - Deadline highlight (if present)
      - Action items / key points
      - Category tag

    Args:
        analysis: The validated EmailAnalysis from the AI analyzer.
        subject:  The original email subject line.

    Returns:
        A MarkdownV2-formatted string ready to be sent via Telegram.
    """
    emoji = IMPORTANCE_EMOJI.get(analysis.importance, "⚪")
    level = IMPORTANCE_LABEL.get(analysis.importance, "UNKNOWN")

    # ── Build the message sections ───────────────────────────────
    lines: list[str] = []

    # Header — Importance badge
    lines.append(f"{emoji} *{_escape_md(level)}* {emoji}")
    lines.append("")

    # Subject
    lines.append(f"📩 *Subject:* {_escape_md(subject)}")

    # Sender
    sender_display = f"{analysis.sender_name} ({analysis.sender_email})"
    lines.append(f"👤 *From:* {_escape_md(sender_display)}")

    # Category
    lines.append(f"🏷️ *Category:* {_escape_md(analysis.category.value)}")
    lines.append("")

    # Separator
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    # Summary
    lines.append(f"📝 *Summary*")
    lines.append(f"{_escape_md(analysis.summary)}")
    lines.append("")

    # Deadline (if present)
    if analysis.deadline:
        lines.append(f"⏰ *Deadline:* {_escape_md(analysis.deadline)}")
        lines.append("")

    # Action Required flag
    if analysis.action_required:
        lines.append("⚡ *Action Required:* Yes")
        lines.append("")

    # Key Points / Action Items
    if analysis.key_points:
        lines.append("📌 *Key Points*")
        for point in analysis.key_points:
            lines.append(f"  • {_escape_md(point)}")
        lines.append("")

    # Footer separator
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🤖 _Analyzed by Gmail Intelligence Agent_")

    return "\n".join(lines)


def format_junk_summary(junk_count: int) -> str:
    """
    Format a brief summary message for filtered junk emails.

    Used to inform the user that junk emails were detected and
    skipped without sending individual notifications.

    Args:
        junk_count: Number of junk emails filtered in this cycle.

    Returns:
        A MarkdownV2-formatted summary string.
    """
    return (
        f"🗑️ *Junk Filter*\n\n"
        f"{_escape_md(str(junk_count))} email\\(s\\) identified as "
        f"promotions/spam and filtered out\\."
    )

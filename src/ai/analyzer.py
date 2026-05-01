"""
Email Analyzer — LangChain LCEL Chain
=======================================
Builds a LangChain chain using the LCEL (LangChain Expression Language)
pattern to analyze emails with GPT-4o-mini and return validated,
structured output via the EmailAnalysis Pydantic schema.

Architecture:
    ChatPromptTemplate  →  ChatOpenAI (with_structured_output)  →  EmailAnalysis

Usage:
    from src.ai.analyzer import EmailAnalyzer

    analyzer = EmailAnalyzer()
    result = analyzer.analyze(sender="...", subject="...", body="...")
    print(result.importance, result.summary)
"""

import logging
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import settings
from src.ai.schemas import EmailAnalysis

logger = logging.getLogger(__name__)

# ── System Prompt ────────────────────────────────────────────────
# This prompt is engineered to:
#   1. Establish the AI's role as an expert email triage assistant
#   2. Define clear classification criteria for importance levels
#   3. Instruct junk/promotion filtering
#   4. Guide structured data extraction
# ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert AI email triage assistant. Your job is to analyze incoming \
emails and extract structured intelligence to help a busy professional manage \
their inbox efficiently.

## Your Tasks
1. **Classify Importance** — Evaluate how urgent and important this email is:
   - **CRITICAL**: Contains hard deadlines (today/tomorrow), urgent requests \
from managers/clients, financial alerts, security warnings, or system outages.
   - **HIGH**: Important business communications, meeting invitations with \
upcoming dates, project updates requiring review, or personal emails from \
close contacts.
   - **MEDIUM**: Useful information that can be reviewed later — FYI updates, \
team announcements, non-urgent requests.
   - **LOW**: Informational content with no action needed — automated reports, \
read-only notifications, general company announcements.
   - **JUNK**: Promotions, marketing emails, newsletters, spam, unsubscribe-able \
content, automated social media notifications, or any mass-sent commercial email.

2. **Filter Junk** — Be aggressive about identifying junk. If the email is \
from a no-reply address, contains marketing language ("sale", "offer", \
"unsubscribe", "limited time"), or is a mass-sent newsletter, mark it as junk.

3. **Extract Summary** — Write a concise 1-3 sentence summary focusing on \
what the sender wants and any key information. Skip greetings and signatures.

4. **Detect Deadlines** — Look for any dates, deadlines, or time-sensitive \
language. Extract the exact date or relative timeframe if present.

5. **Identify Action Items** — List 1-4 concrete action items or key takeaways.

## Rules
- Be concise and professional in your summaries.
- When in doubt between two importance levels, choose the higher one.
- Never fabricate information not present in the email.
- For the sender_name, extract the display name; for sender_email, extract \
the actual email address from the From header.
"""

HUMAN_PROMPT = """\
Analyze the following email:

**From:** {sender}
**Subject:** {subject}
**Date:** {date}

**Body:**
{body}
"""


class EmailAnalyzer:
    """
    LangChain LCEL chain that analyzes a single email and returns
    a validated EmailAnalysis Pydantic object.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
    ) -> None:
        """
        Initialize the LangChain analysis chain.

        Args:
            model_name:  OpenAI model to use. Defaults to settings.OPENAI_MODEL.
            temperature: Sampling temperature. 0.0 for deterministic output.
        """
        model = model_name or settings.OPENAI_MODEL

        # Build the prompt template
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ])

        # Build the LLM with structured output binding
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
            max_retries=2,
        ).with_structured_output(EmailAnalysis)

        # LCEL Chain:  Prompt → LLM → EmailAnalysis
        self._chain = self._prompt | self._llm

        logger.info(
            "EmailAnalyzer initialized (model=%s, temperature=%s).",
            model,
            temperature,
        )

    def analyze(
        self,
        sender: str,
        subject: str,
        body: str,
        date: str = "",
    ) -> EmailAnalysis:
        """
        Analyze a single email and return structured intelligence.

        Args:
            sender:  The From header value (e.g., "Alice <alice@example.com>").
            subject: The email subject line.
            body:    The decoded plain-text email body.
            date:    The Date header value (optional).

        Returns:
            A validated EmailAnalysis Pydantic object containing importance,
            summary, deadline, action items, and more.

        Raises:
            Exception: On LLM API failure after retries.
        """
        # Truncate very long email bodies to stay within context limits
        truncated_body = body[:8000] if len(body) > 8000 else body

        logger.debug(
            "Analyzing email — Subject: '%s' | From: '%s'", subject, sender
        )

        result: EmailAnalysis = self._chain.invoke({
            "sender": sender,
            "subject": subject,
            "body": truncated_body,
            "date": date,
        })

        logger.info(
            "Analysis complete — Importance: %s | Junk: %s | Subject: '%s'",
            result.importance.value,
            result.is_junk,
            subject[:60],
        )

        return result

"""
analyzer.py — Calls Claude API with prospect data, parses JSON response.
Retries once after RETRY_DELAY seconds on failure.
"""

import json
import time
import logging

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    SERVICE_OFFERING,
    RETRY_DELAY,
)

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─── Prompt builder ──────────────────────────────────────────────────────────

def _build_prompt(row: dict) -> str:
    return f"""
You are a world-class B2B copywriter creating a hyper-personalised landing page
for a UAE-based growth agency. Your task is to write copy that makes the prospect
feel this page was built just for them.

=== OUR SERVICE OFFERING ===
{SERVICE_OFFERING.strip()}

=== PROSPECT DATA ===
First name:          {row.get('First name', '')}
Last name:           {row.get('Last name', '')}
Job title:           {row.get('Job title', '')}
Persona:             {row.get('Persona', '')}
Tier:                {row.get('Tier', '')}
Company:             {row.get('Company', '')}
Industry:            {row.get('Industry', '')}
Sub-Industry:        {row.get('Sub-Industry', '')}
Company Size:        {row.get('Company Size', '')}
Revenue (AED):       {row.get('Revenue_Estimate_AED', '')}
Core Service:        {row.get('Core_Service', '')}
Recent News:         {row.get('Recent_News', '')}
Pain Point 1:        {row.get('Pain_1', '')}
Pain Point 2:        {row.get('Pain_2', '')}
Pain Point 3:        {row.get('Pain_3', '')}
WA Use Case:         {row.get('WA_Use_Case', '')}
Cold Email Hook:     {row.get('Cold_Email_Hook', '')}
LinkedIn Hook:       {row.get('LinkedIn_Hook', '')}
Research Confidence: {row.get('Research_Confidence', '')}
Research Notes:      {row.get('Research_Notes', '')}

=== INSTRUCTIONS ===
Return ONLY a valid JSON object — no markdown fences, no explanation, no trailing
text. Use exactly these keys:

{{
  "hero_headline":      "1 punchy line. Mention company name. Use Cold_Email_Hook
                         as inspiration. Tier 1 = bold ROI claim. Tier 2 = insight-led.
                         Tier 3 = question-led.",
  "hero_subheadline":   "1 sentence expanding on the headline using Recent_News
                         as context. Sound like you did your homework.",
  "opener":             "2 sentences. Address them by First name. Reference
                         Core_Service and one specific detail from Recent_News or
                         Research_Notes. Tone by Persona: Founder/CEO=ROI,
                         Marketing=growth, Operations=efficiency, Finance=cost/risk,
                         Sales=pipeline, Tech/CTO=automation, Other=value.
                         Tone by Research_Confidence: High=assertive,
                         Medium=confident, Low=curious/question-based.",
  "pain_1_title":       "4-6 word title for Pain_1",
  "pain_1_body":        "Pain_1 rewritten as 1 clear sentence (not a fragment)",
  "pain_2_title":       "4-6 word title for Pain_2",
  "pain_2_body":        "Pain_2 rewritten as 1 clear sentence",
  "pain_3_title":       "4-6 word title for Pain_3",
  "pain_3_body":        "Pain_3 rewritten as 1 clear sentence",
  "solution_1_title":   "Our service that solves Pain_1 (4-6 words)",
  "solution_1_body":    "1 sentence: how we solve it, specific to them",
  "solution_2_title":   "Our service that solves Pain_2 (4-6 words)",
  "solution_2_body":    "1 sentence: how we solve it, specific to them",
  "solution_3_title":   "Our service that solves Pain_3 (4-6 words)",
  "solution_3_body":    "1 sentence: how we solve it, specific to them",
  "wa_use_case_title":  "5-7 word title for WA_Use_Case",
  "wa_use_case_body":   "WA_Use_Case rewritten as 2 punchy sentences",
  "company_context":    "2 sentences. Professional insight combining Core_Service
                         and Recent_News — NOT the raw CSV text.",
  "cta_headline":       "Tier 1: Let's build [Company]'s growth engine this quarter.
                         Tier 2: Here's what we'd do for [Company] in 30 days.
                         Tier 3: Want to see what's possible for [Company]?",
  "cta_button_text":    "3-5 words. Persona-aware: Founder/CEO=Book a Strategy Call,
                         Marketing=See Our Growth Plan,
                         Operations/Finance=Get a Free Audit, Others=Let's Talk"
}}

Write like a senior strategist who has genuinely researched this company — not
like a template filler. Every sentence must feel earned.
""".strip()


# ─── JSON extractor ──────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """
    Extract a JSON object from the model response.
    Handles accidental markdown fences or preamble text.
    """
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()
    # Find the first '{' and last '}'
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in Claude response.")
    return json.loads(text[start:end])


# ─── Public API ──────────────────────────────────────────────────────────────

REQUIRED_KEYS = {
    "hero_headline", "hero_subheadline", "opener",
    "pain_1_title", "pain_1_body",
    "pain_2_title", "pain_2_body",
    "pain_3_title", "pain_3_body",
    "solution_1_title", "solution_1_body",
    "solution_2_title", "solution_2_body",
    "solution_3_title", "solution_3_body",
    "wa_use_case_title", "wa_use_case_body",
    "company_context",
    "cta_headline", "cta_button_text",
}


def generate_page_content(row: dict) -> dict:
    """
    Call Claude and return a validated dict of page-copy fields.
    Retries once on any failure. Raises on second failure.
    """
    prompt = _build_prompt(row)
    label  = f"{row.get('First name', '?')} at {row.get('Company', '?')}"

    for attempt in range(1, 3):
        try:
            response = _client.messages.create(
                model      = CLAUDE_MODEL,
                max_tokens = 2048,
                thinking   = {"type": "adaptive"},
                messages   = [{"role": "user", "content": prompt}],
            )
            # Extract text content (thinking blocks come first — skip them)
            text_content = next(
                (block.text for block in response.content if block.type == "text"),
                None,
            )
            if not text_content:
                raise ValueError("Claude returned no text content.")

            data = _extract_json(text_content)

            missing = REQUIRED_KEYS - data.keys()
            if missing:
                raise ValueError(f"Claude JSON missing keys: {missing}")

            return data

        except (anthropic.APIError, anthropic.APIConnectionError,
                anthropic.RateLimitError) as exc:
            if attempt == 1:
                logger.warning(
                    "Claude API error for %s (attempt %d): %s — retrying in %ss",
                    label, attempt, exc, RETRY_DELAY
                )
                time.sleep(RETRY_DELAY)
            else:
                raise

        except (json.JSONDecodeError, ValueError) as exc:
            if attempt == 1:
                logger.warning(
                    "JSON parse error for %s (attempt %d): %s — retrying in %ss",
                    label, attempt, exc, RETRY_DELAY
                )
                time.sleep(RETRY_DELAY)
            else:
                raise

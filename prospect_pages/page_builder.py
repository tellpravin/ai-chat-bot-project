"""
page_builder.py — Jinja2 rendering, slugification, duplicate name handling.
"""

import os
import re
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import (
    BRAND_NAME,
    CALENDLY_LINK,
    ABOUT_US,
    TESTIMONIALS,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)

# ─── Jinja2 environment ──────────────────────────────────────────────────────
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader      = FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape  = select_autoescape(["html"]),
)


# ─── Slug helpers ────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convert any string to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)      # remove special chars
    text = re.sub(r"[\s_]+", "-", text)        # spaces/underscores → hyphens
    text = re.sub(r"-{2,}", "-", text)         # collapse multiple hyphens
    return text.strip("-")


def build_slug(company: str, first_name: str, used_slugs: set) -> str:
    """
    Return a unique slug for the prospect.
    If two prospects share a company slug, append the first name.
    """
    base = _slugify(company)
    if base not in used_slugs:
        used_slugs.add(base)
        return base
    # Collision — append first name
    extended = f"{base}-{_slugify(first_name)}"
    if extended not in used_slugs:
        used_slugs.add(extended)
        return extended
    # Edge case: same company AND same first name — append counter
    counter = 2
    while True:
        candidate = f"{extended}-{counter}"
        if candidate not in used_slugs:
            used_slugs.add(candidate)
            return candidate
        counter += 1


# ─── Public render function ──────────────────────────────────────────────────

def render_page(row: dict, content: dict, slug: str) -> str:
    """
    Render the Jinja2 template and save to OUTPUT_DIR/<slug>.html.
    Returns the local file path.
    """
    template = _env.get_template("landing.html")

    context = {
        # ── Brand / static ──────────────────────────────────────────────────
        "brand_name":   BRAND_NAME,
        "calendly_link": CALENDLY_LINK,
        "about_us":     ABOUT_US,
        "testimonials": TESTIMONIALS,

        # ── Prospect CSV fields ──────────────────────────────────────────────
        "first_name":      row.get("First name", ""),
        "last_name":       row.get("Last name", ""),
        "company":         row.get("Company", ""),
        "job_title":       row.get("Job title", ""),
        "industry":        row.get("Industry", ""),
        "sub_industry":    row.get("Sub-Industry", ""),
        "company_size":    row.get("Company Size", ""),
        "revenue_aed":     row.get("Revenue_Estimate_AED", ""),
        "core_service":    row.get("Core_Service", ""),
        "recent_news":     row.get("Recent_News", ""),
        "tier":            str(row.get("Tier", "")),
        "website":         row.get("Website Clean", ""),

        # ── Claude-generated copy ────────────────────────────────────────────
        **content,
    }

    html = template.render(**context)

    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{slug}.html"
    file_path.write_text(html, encoding="utf-8")
    logger.info("Saved page: %s", file_path)
    return str(file_path)

"""
main.py — Orchestrator: reads CSV → calls Claude → builds HTML → deploys.
"""

import csv
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from github import GithubException

from config import (
    CSV_FILE,
    CSV_ENCODING,
    RESULTS_CSV,
    ERRORS_CSV,
    DELAY_BETWEEN_CALLS,
    GITHUB_USERNAME,
    GITHUB_REPO,
)
from analyzer    import generate_page_content
from page_builder import build_slug, render_page
from deploy      import push_page

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt = "%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ─── CSV helpers ─────────────────────────────────────────────────────────────

def _init_results_csv():
    if not Path(RESULTS_CSV).exists():
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "First name", "Last name", "Company", "Job title",
                "Tier", "Email", "Industry", "Personalized_URL",
                "Status", "Timestamp",
            ])
            writer.writeheader()


def _init_errors_csv():
    if not Path(ERRORS_CSV).exists():
        with open(ERRORS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "First name", "Company", "Tier", "Email",
                "Error_Type", "Error_Detail", "Timestamp",
            ])
            writer.writeheader()


def _append_result(row: dict, url: str, status: str):
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "First name", "Last name", "Company", "Job title",
            "Tier", "Email", "Industry", "Personalized_URL",
            "Status", "Timestamp",
        ])
        writer.writerow({
            "First name":      row.get("First name", ""),
            "Last name":       row.get("Last name", ""),
            "Company":         row.get("Company", ""),
            "Job title":       row.get("Job title", ""),
            "Tier":            row.get("Tier", ""),
            "Email":           row.get("Email", ""),
            "Industry":        row.get("Industry", ""),
            "Personalized_URL": url,
            "Status":          status,
            "Timestamp":       datetime.now(timezone.utc).isoformat(),
        })


def _append_error(row: dict, error_type: str, detail: str):
    with open(ERRORS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "First name", "Company", "Tier", "Email",
            "Error_Type", "Error_Detail", "Timestamp",
        ])
        writer.writerow({
            "First name":   row.get("First name", ""),
            "Company":      row.get("Company", ""),
            "Tier":         row.get("Tier", ""),
            "Email":        row.get("Email", ""),
            "Error_Type":   error_type,
            "Error_Detail": str(detail)[:2000],
            "Timestamp":    datetime.now(timezone.utc).isoformat(),
        })


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    # ── Load CSV ──────────────────────────────────────────────────────────────
    logger.info("Loading CSV: %s", CSV_FILE)
    df = pd.read_csv(CSV_FILE, encoding=CSV_ENCODING)

    # Clean: drop rows missing Email or Company
    before = len(df)
    df = df[df["Email"].notna() & df["Email"].str.strip().ne("")]
    df = df[df["Company"].notna() & df["Company"].str.strip().ne("")]
    logger.info("Dropped %d incomplete rows. Processing %d prospects.", before - len(df), len(df))

    # Sort by Tier ascending (Tier 1 first)
    df["Tier"] = pd.to_numeric(df["Tier"], errors="coerce").fillna(99).astype(int)
    df = df.sort_values("Tier").reset_index(drop=True)

    total = len(df)

    # ── Init output files ─────────────────────────────────────────────────────
    _init_results_csv()
    _init_errors_csv()

    # ── Counters ──────────────────────────────────────────────────────────────
    deployed   = 0
    failed     = 0
    local_only = 0
    tier_counts = {1: 0, 2: 0, 3: 0}
    used_slugs: set = set()

    # ── Process each prospect ─────────────────────────────────────────────────
    for idx, row in df.iterrows():
        n          = idx + 1
        first_name = row.get("First name", "?")
        company    = row.get("Company", "?")
        tier       = int(row.get("Tier", 0))
        print(f"\nProcessing [{n}/{total}]: {first_name} at {company} (Tier {tier})...")

        # ── Build slug ──────────────────────────────────────────────────────
        slug = build_slug(str(company), str(first_name), used_slugs)

        # ── Call Claude ─────────────────────────────────────────────────────
        content = None
        try:
            content = generate_page_content(row.to_dict())
        except Exception as exc:
            logger.error("Claude failed for %s @ %s: %s", first_name, company, exc)
            _append_error(row.to_dict(), "claude_api_error", str(exc))
            _append_result(row.to_dict(), "", "failed")
            failed += 1
            time.sleep(DELAY_BETWEEN_CALLS)
            continue

        # ── Render HTML ─────────────────────────────────────────────────────
        try:
            local_path = render_page(row.to_dict(), content, slug)
        except Exception as exc:
            logger.error("Render failed for %s @ %s: %s", first_name, company, exc)
            _append_error(row.to_dict(), "render_error", str(exc))
            _append_result(row.to_dict(), "", "failed")
            failed += 1
            time.sleep(DELAY_BETWEEN_CALLS)
            continue

        # ── Deploy to GitHub Pages ──────────────────────────────────────────
        try:
            url = push_page(local_path, slug)
            logger.info("Deployed: %s → %s", slug, url)
            _append_result(row.to_dict(), url, "success")
            deployed += 1
            if tier in tier_counts:
                tier_counts[tier] += 1
        except GithubException as exc:
            expected_url = (
                f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/pages/{slug}.html"
            )
            logger.warning(
                "GitHub push failed for %s (saved locally): %s", slug, exc
            )
            _append_error(row.to_dict(), "github_push_error", str(exc))
            _append_result(row.to_dict(), expected_url, "local_only")
            local_only += 1
            if tier in tier_counts:
                tier_counts[tier] += 1  # still count as processed

        time.sleep(DELAY_BETWEEN_CALLS)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print(
        f"✓ {deployed} pages deployed  |  "
        f"⚠ {local_only} local only  |  "
        f"✗ {failed} failed"
    )
    print(
        f"Tier 1: {tier_counts[1]}  |  "
        f"Tier 2: {tier_counts[2]}  |  "
        f"Tier 3: {tier_counts[3]}"
    )
    print("═" * 60)
    logger.info("Run complete. Results: %s  Errors: %s", RESULTS_CSV, ERRORS_CSV)


if __name__ == "__main__":
    main()

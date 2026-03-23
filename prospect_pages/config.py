"""
config.py — All constants, credentials, and brand content.
Replace every [PLACEHOLDER] block with your real data before running.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── API & GitHub ────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN        = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME     = os.getenv("GITHUB_USERNAME", "yourusername")
GITHUB_REPO         = os.getenv("GITHUB_REPO", "prospect-pages")
CALENDLY_LINK       = os.getenv("CALENDLY_LINK", "https://calendly.com/yourlink")
BRAND_NAME          = os.getenv("BRAND_NAME", "GrowthLab UAE")

# ─── Claude model ────────────────────────────────────────────────────────────
CLAUDE_MODEL        = "claude-opus-4-6"

# ─── CSV ─────────────────────────────────────────────────────────────────────
CSV_FILE            = "Enriched_Ecommerce_B2B_Research_Cleaned.csv"
CSV_ENCODING        = "latin-1"

# ─── Output ──────────────────────────────────────────────────────────────────
OUTPUT_DIR          = "output/pages"
RESULTS_CSV         = "results.csv"
ERRORS_CSV          = "errors.csv"

# ─── Rate limiting ───────────────────────────────────────────────────────────
DELAY_BETWEEN_CALLS = 1.5   # seconds between Claude API calls
RETRY_DELAY         = 5.0   # seconds before retrying a failed Claude call

# ─── Brand / About Us (static, same on every page) ───────────────────────────
ABOUT_US = {
    "headline": "Who We Are",
    "body": (
        f"{BRAND_NAME} is a Dubai-based growth agency specialising in revenue "
        "acceleration for UAE ecommerce and retail brands. We combine data-driven "
        "paid media, conversion-rate optimisation, and WhatsApp automation to "
        "deliver measurable results — not vanity metrics."
    ),
    "services": [
        "WhatsApp Marketing Automation & Broadcast Sequences",
        "Shopify Store Optimisation & CRO",
        "Meta & Google Paid Ads Management",
        "Email Marketing Flows (Klaviyo / Mailchimp)",
        "Post-Purchase Retention Systems",
    ],
    "location": "Dubai, UAE",
    "tagline": "Typical clients see 25–40 % revenue uplift within 90 days.",
}

# ─── Service offering (injected into every Claude prompt) ────────────────────
SERVICE_OFFERING = """
We help UAE-based ecommerce and retail brands grow revenue through:
- WhatsApp marketing automation and broadcast sequences
- Shopify store optimisation and CRO
- Meta and Google paid ads management
- Email marketing flows (Klaviyo / Mailchimp)
- Post-purchase retention systems
Our typical client sees 25-40% revenue uplift within 90 days.
"""

# ─── Testimonials (static, same on every page) ───────────────────────────────
TESTIMONIALS = [
    {
        "quote": (
            "Within 60 days of working with the team, our WhatsApp "
            "repeat-purchase rate jumped by 32%. The sequences feel human, "
            "not spammy — customers actually reply."
        ),
        "name":    "Sarah Al-Mansouri",
        "company": "Bloom & Co.",
        "role":    "Founder & CEO",
    },
    {
        "quote": (
            "They rebuilt our Shopify checkout flow and our abandoned-cart "
            "recovery went from 8 % to 21 % in six weeks. Straight ROI."
        ),
        "name":    "James Whitfield",
        "company": "Urban Essentials",
        "role":    "Head of Ecommerce",
    },
    {
        "quote": (
            "The Meta ads strategy they brought was completely different from "
            "what we'd tried before. ROAS went from 1.8x to 4.2x in 45 days."
        ),
        "name":    "Nour Haddad",
        "company": "The Gift Studio",
        "role":    "Co-Founder & COO",
    },
]

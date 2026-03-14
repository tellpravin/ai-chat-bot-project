#!/usr/bin/env python3
"""
Data.xlsx Processor
Generates 4 CSV files for Apollo, PhantomBuster, Instantly, and industry classification.
"""

import os
import sys
import base64
import re
import pandas as pd

WORKDIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(WORKDIR, "Data.xlsx")

# ── Persona mapping ──────────────────────────────────────────────────────────
FOUNDER_CEO_KEYWORDS = [
    "founder", "co-founder", "ceo", "chief executive",
    "owner", "managing director", "md", "president", "director"
]
MARKETING_KEYWORDS = [
    "marketing", "growth", "brand", "content", "seo",
    "digital", "demand", "acquisition", "cmo", "cmoo"
]
SALES_KEYWORDS = [
    "sales", "business development", "account", "revenue",
    "partnerships", "commercial", "cso", "vp sales"
]

def classify_persona(title: str) -> str:
    if not isinstance(title, str):
        return "Other"
    t = title.lower()
    if any(k in t for k in FOUNDER_CEO_KEYWORDS):
        return "Founder/CEO"
    if any(k in t for k in MARKETING_KEYWORDS):
        return "Marketing"
    if any(k in t for k in SALES_KEYWORDS):
        return "Sales"
    return "Other"

PERSONA_ORDER = {"Founder/CEO": 0, "Marketing": 1, "Sales": 2, "Other": 3}

# ── Domain extraction ────────────────────────────────────────────────────────
def extract_domain(url) -> str:
    if not isinstance(url, str) or not url.strip():
        return ""
    url = url.strip().lower()
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    url = url.split("/")[0]
    return url

# ── Industry classification (rule-based, no web calls needed) ────────────────
INDUSTRY_RULES = {
    "Fashion/Apparel": [
        "fashion", "apparel", "cloth", "wear", "dress", "shirt", "trouser",
        "jeans", "shoe", "footwear", "kurti", "saree", "lehenga", "ethnic",
        "textile", "garment", "boutique", "style", "outfit"
    ],
    "Electronics": [
        "electron", "gadget", "mobile", "phone", "laptop", "computer",
        "tech", "device", "smart", "appliance", "led", "tv", "camera"
    ],
    "Beauty/Skincare": [
        "beauty", "skin", "care", "cosmetic", "makeup", "lip", "hair",
        "nail", "spa", "salon", "groom", "fragrance", "perfume", "serum"
    ],
    "Food/Grocery": [
        "food", "grocer", "snack", "eat", "kitchen", "spice", "organic",
        "dairy", "bakery", "cafe", "restaurant", "meal", "nutrition", "diet"
    ],
    "Home/Furniture": [
        "home", "furniture", "decor", "interior", "living", "sofa", "bed",
        "mattress", "curtain", "lamp", "rug", "storage", "kitchen ware"
    ],
    "Gifts/Flowers": [
        "gift", "flower", "floral", "bouquet", "hamper", "occasion",
        "greeting", "wedding", "birthday", "anniversary", "celebration"
    ],
    "Opticals": [
        "optic", "optical", "eyewear", "spectacle", "glass", "lens",
        "contact lens", "sunglass", "vision", "eye care"
    ],
    "Books/Stationery": [
        "book", "station", "publish", "paper", "pen", "note", "journal",
        "library", "education", "learning", "school supply"
    ],
    "Sports": [
        "sport", "fitness", "gym", "yoga", "outdoor", "cycling", "run",
        "athletic", "exercise", "health", "wellness", "activewear"
    ],
}

def classify_industry(company: str, website: str) -> tuple[str, str]:
    text = f"{company} {website}".lower()
    scores: dict[str, int] = {}
    for industry, keywords in INDUSTRY_RULES.items():
        score = sum(1 for k in keywords if k in text)
        if score:
            scores[industry] = score
    if not scores:
        return "Other", "Low"
    best = max(scores, key=lambda k: scores[k])
    top_score = scores[best]
    confidence = "High" if top_score >= 3 else ("Medium" if top_score == 2 else "Low")
    return best, confidence

# ── Load data ────────────────────────────────────────────────────────────────
def load_excel(path: str) -> pd.DataFrame:
    print(f"\n📂  Reading {path} …")
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = df.columns.str.strip()
    print(f"    Loaded {len(df):,} rows × {len(df.columns)} columns")
    print(f"    Columns: {list(df.columns)}\n")
    return df

# ── Column detection ─────────────────────────────────────────────────────────
def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None

def resolve_columns(df: pd.DataFrame) -> dict:
    mapping = {
        "first_name": find_col(df, ["First Name", "FirstName", "first_name", "fname"]),
        "last_name":  find_col(df, ["Last Name",  "LastName",  "last_name",  "lname"]),
        "email":      find_col(df, ["Email", "Email Address", "email_address"]),
        "company":    find_col(df, ["Company", "Company Name", "Organisation", "Organization"]),
        "website":    find_col(df, ["Website", "Website URL", "Domain", "URL"]),
        "job_title":  find_col(df, ["Job Title", "Title", "Position", "Role", "Designation"]),
        "linkedin":   find_col(df, ["LinkedIn URL", "LinkedIn", "linkedin_url", "Profile URL"]),
    }
    print("  Column mapping:")
    for k, v in mapping.items():
        status = f"→ '{v}'" if v else "✗ NOT FOUND (will be blank)"
        print(f"    {k:<12} {status}")
    print()
    return mapping

# ── Analysis ─────────────────────────────────────────────────────────────────
def print_analysis(df: pd.DataFrame):
    print("=" * 60)
    print("DATA QUALITY ANALYSIS")
    print("=" * 60)
    print(f"Total rows : {len(df):,}")
    print(f"Columns    : {len(df.columns)}\n")

    print(f"{'Column':<30} {'Type':<15} {'Missing':>8} {'Complete %':>10}")
    print("-" * 65)
    for col in df.columns:
        missing = int(df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
        pct = round((1 - missing / len(df)) * 100, 1)
        dtype = str(df[col].dtype)
        print(f"{col:<30} {dtype:<15} {missing:>8,} {pct:>9.1f}%")
    print()

# ── FILE 1: apollo_upload.csv ────────────────────────────────────────────────
def make_apollo(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    print("⚙  Building apollo_upload.csv …")

    # add persona column
    title_col = cols["job_title"]
    df["_Persona"] = df[title_col].apply(classify_persona) if title_col else "Other"

    # filter: target personas only
    target = df[df["_Persona"].isin(["Founder/CEO", "Marketing", "Sales"])].copy()

    # filter: missing email
    if cols["email"]:
        missing_email = (
            target[cols["email"]].isna() |
            target[cols["email"]].astype(str).str.strip().eq("") |
            target[cols["email"]].astype(str).str.strip().eq("nan")
        )
        target = target[missing_email].copy()

    out = pd.DataFrame()
    out["First Name"] = target[cols["first_name"]].fillna("") if cols["first_name"] else ""
    out["Last Name"]  = target[cols["last_name"]].fillna("")  if cols["last_name"]  else ""
    out["Company"]    = target[cols["company"]].fillna("")    if cols["company"]    else ""
    out["Domain"]     = target[cols["website"]].apply(extract_domain) if cols["website"] else ""

    path = os.path.join(WORKDIR, "apollo_upload.csv")
    out.to_csv(path, index=False)
    return out, path

# ── FILE 2: linkedin_urls_to_resolve.csv ────────────────────────────────────
def make_linkedin(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    print("⚙  Building linkedin_urls_to_resolve.csv …")
    out = pd.DataFrame()
    out["First Name"]    = df[cols["first_name"]].fillna("") if cols["first_name"] else ""
    out["Last Name"]     = df[cols["last_name"]].fillna("")  if cols["last_name"]  else ""
    out["Company"]       = df[cols["company"]].fillna("")    if cols["company"]    else ""
    out["LinkedIn URL"]  = df[cols["linkedin"]].fillna("")   if cols["linkedin"]   else ""

    path = os.path.join(WORKDIR, "linkedin_urls_to_resolve.csv")
    out.to_csv(path, index=False)
    return out, path

# ── FILE 3: instantly_ready.csv ──────────────────────────────────────────────
def make_instantly(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    print("⚙  Building instantly_ready.csv …")

    title_col = cols["job_title"]
    df["_Persona"] = df[title_col].apply(classify_persona) if title_col else "Other"

    # keep only rows with a verified (non-empty) email
    if cols["email"]:
        has_email = (
            df[cols["email"]].notna() &
            df[cols["email"]].astype(str).str.strip().ne("") &
            df[cols["email"]].astype(str).str.strip().ne("nan")
        )
        verified = df[has_email].copy()
    else:
        verified = df.copy()

    # sort by persona priority
    verified["_sort"] = verified["_Persona"].map(PERSONA_ORDER).fillna(99)
    verified = verified.sort_values("_sort").drop(columns=["_sort"])

    out = pd.DataFrame()
    out["First Name"]   = verified[cols["first_name"]].fillna("") if cols["first_name"] else ""
    out["Last Name"]    = verified[cols["last_name"]].fillna("")  if cols["last_name"]  else ""
    out["Email"]        = verified[cols["email"]].fillna("")      if cols["email"]      else ""
    out["Company"]      = verified[cols["company"]].fillna("")    if cols["company"]    else ""
    out["Job Title"]    = verified[cols["job_title"]].fillna("")  if cols["job_title"]  else ""
    out["Persona"]      = verified["_Persona"]
    out["LinkedIn URL"] = verified[cols["linkedin"]].fillna("")   if cols["linkedin"]   else ""

    path = os.path.join(WORKDIR, "instantly_ready.csv")
    out.to_csv(path, index=False)
    return out, path

# ── FILE 4: industry_classify.csv ────────────────────────────────────────────
def make_industry(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    print("⚙  Building industry_classify.csv …")

    company_col = cols["company"]
    website_col = cols["website"]

    if company_col:
        companies = df[[company_col] + ([website_col] if website_col else [])].drop_duplicates(subset=[company_col])
    else:
        print("    WARNING: No company column found — skipping industry file.")
        return pd.DataFrame(), ""

    rows = []
    for _, row in companies.iterrows():
        company = str(row[company_col]).strip() if company_col else ""
        website = str(row[website_col]).strip() if website_col else ""
        if company.lower() in ("", "nan"):
            continue
        industry, confidence = classify_industry(company, website)
        rows.append({
            "Company":           company,
            "Website":           website if website != "nan" else "",
            "Industry Category": industry,
            "Confidence":        confidence,
        })

    out = pd.DataFrame(rows)
    path = os.path.join(WORKDIR, "industry_classify.csv")
    out.to_csv(path, index=False)
    return out, path

# ── Data quality summary ──────────────────────────────────────────────────────
def make_quality_summary(df: pd.DataFrame, cols: dict,
                         apollo: pd.DataFrame, instantly: pd.DataFrame):
    print("⚙  Building data_quality_summary.csv …")

    total = len(df)
    email_col = cols["email"]

    if email_col:
        has_email = (
            df[email_col].notna() &
            df[email_col].astype(str).str.strip().ne("") &
            df[email_col].astype(str).str.strip().ne("nan")
        )
        emails_before = int(has_email.sum())
    else:
        emails_before = 0

    emails_after = emails_before + len(apollo)   # apollo rows are enrichment candidates

    rows = [
        {"Metric": "Total Contacts",              "Before Enrichment": total,          "After Enrichment (est.)": total},
        {"Metric": "Contacts WITH Email",          "Before Enrichment": emails_before,  "After Enrichment (est.)": emails_after},
        {"Metric": "Contacts MISSING Email",       "Before Enrichment": total - emails_before, "After Enrichment (est.)": total - emails_after},
        {"Metric": "Email Completion %",           "Before Enrichment": f"{emails_before/total*100:.1f}%", "After Enrichment (est.)": f"{emails_after/total*100:.1f}%"},
        {"Metric": "Apollo Upload Candidates",     "Before Enrichment": len(apollo),    "After Enrichment (est.)": 0},
        {"Metric": "Instantly Ready (verified)",   "Before Enrichment": len(instantly), "After Enrichment (est.)": emails_after},
    ]

    out = pd.DataFrame(rows)
    path = os.path.join(WORKDIR, "data_quality_summary.csv")
    out.to_csv(path, index=False)
    return out, path

# ── Preview helper ────────────────────────────────────────────────────────────
def preview(name: str, df: pd.DataFrame, path: str):
    print(f"\n{'─'*60}")
    print(f"  FILE : {name}")
    print(f"  PATH : {path}")
    print(f"  ROWS : {len(df):,}")
    print(f"  COLS : {list(df.columns)}")
    print("  PREVIEW (first 3 rows):")
    print(df.head(3).to_string(index=False))
    print()

# ── Base64 intake ─────────────────────────────────────────────────────────────
def accept_base64():
    print("\n📋  Data.xlsx not found.")
    print("    Paste the Base64 string (from data_base64.txt) and press Enter twice:\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines:
            break
        lines.append(line.strip())

    b64 = "".join(lines)
    try:
        data = base64.b64decode(b64)
    except Exception as e:
        print(f"✗  Invalid Base64: {e}")
        sys.exit(1)

    with open(XLSX_PATH, "wb") as f:
        f.write(data)
    print(f"✅  Saved decoded file → {XLSX_PATH}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("  DATA.XLSX PROCESSOR")
    print("=" * 60)

    if not os.path.exists(XLSX_PATH):
        accept_base64()

    df = load_excel(XLSX_PATH)
    print_analysis(df)
    cols = resolve_columns(df)

    apollo,    apollo_path    = make_apollo(df, cols)
    linkedin,  linkedin_path  = make_linkedin(df, cols)
    instantly, instantly_path = make_instantly(df, cols)
    industry,  industry_path  = make_industry(df, cols)
    summary,   summary_path   = make_quality_summary(df, cols, apollo, instantly)

    print("\n" + "=" * 60)
    print("  OUTPUT FILES")
    print("=" * 60)
    preview("apollo_upload.csv",              apollo,    apollo_path)
    preview("linkedin_urls_to_resolve.csv",   linkedin,  linkedin_path)
    preview("instantly_ready.csv",            instantly, instantly_path)
    preview("industry_classify.csv",          industry,  industry_path)
    preview("data_quality_summary.csv",       summary,   summary_path)

    print("=" * 60)
    print("  ALL FILES GENERATED SUCCESSFULLY")
    print(f"  Location: {WORKDIR}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()

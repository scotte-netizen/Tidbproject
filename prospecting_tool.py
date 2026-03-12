#!/usr/bin/env python3
"""Prospecting brief generator for non-technical sales discovery calls.

This script collects basic lead/account inputs and creates a markdown brief with:
1) Person background
2) Company background
3) Technology overview
4) Potential pitfalls
5) Fit for TiDB
6) Discovery questions
7) Role assessment
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import site
import ssl
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List
from urllib.parse import urlparse

@dataclass
class ProspectInputs:
    company_name: str
    person_name: str
    linkedin_profile: str
    company_website: str
    tech_stack: str


def ensure_dependencies() -> bool:
    """Install missing runtime dependencies automatically.

    Returns True if optional dependencies are available after check/install,
    else False (the script will use standard-library fallback behavior).
    """
    package_to_import = {
        "requests": "requests",
        "beautifulsoup4": "bs4",
    }
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")

    missing = []
    for package_name, module_name in package_to_import.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)

    needs_urllib3_downgrade = False
    if not missing:
        try:
            urllib3 = importlib.import_module("urllib3")
            major_version = int(str(getattr(urllib3, "__version__", "0")).split(".", maxsplit=1)[0])
            needs_urllib3_downgrade = "LibreSSL" in ssl.OPENSSL_VERSION and major_version >= 2
        except (ImportError, ValueError):
            needs_urllib3_downgrade = False

    if not missing and not needs_urllib3_downgrade:
        return True

    if missing:
        print(f"[info] Missing dependencies detected: {', '.join(missing)}")
    if needs_urllib3_downgrade:
        print("[info] Detected urllib3/OpenSSL compatibility issue. Installing pinned dependencies...")

    try:
        if os.path.exists(requirements_path):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
        else:
            print("[info] requirements.txt not found. Installing dependencies with pip...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        importlib.invalidate_caches()

        # pip may install into the user site-packages directory, which is not
        # always on sys.path for the current process until a new interpreter starts.
        user_site = site.getusersitepackages()
        if user_site and user_site not in sys.path:
            sys.path.append(user_site)

        for package_name, module_name in package_to_import.items():
            importlib.import_module(module_name)

        return True
    except subprocess.CalledProcessError:
        print("[warn] Could not install optional dependencies due to environment restrictions.")
        print("[warn] Continuing with built-in parser fallback.")
        return False
    except ImportError as exc:
        print(f"[warn] Dependencies installed but could not be imported in this session ({exc}).")
        print("[warn] Continuing with built-in parser fallback.")
        return False


def safe_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_website_summary(url: str, use_optional_deps: bool) -> dict:
    """Fetch title, description and short visible text from the company website."""
    if not url:
        return {"title": "Not provided", "description": "Not available", "snippet": "Not available"}

    try:
        if use_optional_deps:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            title = safe_text(soup.title.get_text()) if soup.title else "Not available"
            desc_tag = soup.find("meta", attrs={"name": "description"})
            description = safe_text(desc_tag["content"]) if desc_tag and desc_tag.get("content") else "Not available"

            for bad in soup(["script", "style", "noscript"]):
                bad.extract()
            visible_text = safe_text(" ".join(soup.get_text(separator=" ").split()))
        else:
            from urllib.request import Request, urlopen

            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=12) as response:  # noqa: S310
                html = response.read().decode("utf-8", errors="ignore")

            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
            title = safe_text(title_match.group(1)) if title_match else "Not available"
            meta_match = re.search(
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            description = safe_text(meta_match.group(1)) if meta_match else "Not available"

            cleaned = re.sub(r"<script.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
            cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            visible_text = safe_text(cleaned)

        snippet = visible_text[:400] + ("..." if len(visible_text) > 400 else "")

        return {
            "title": title,
            "description": description,
            "snippet": snippet or "Not available",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "title": "Not available",
            "description": f"Could not fetch website details ({exc}).",
            "snippet": "Not available",
        }


def parse_stack(tech_stack: str) -> List[str]:
    if not tech_stack.strip():
        return []
    raw = re.split(r"[,/;|]", tech_stack)
    return [safe_text(item) for item in raw if safe_text(item)]


def fit_for_tidb(stack_items: List[str]) -> str:
    stack_lower = [item.lower() for item in stack_items]

    transactional_signals = ["mysql", "postgres", "mongodb", "kafka", "microservices", "kubernetes", "aws", "gcp", "azure"]
    scale_signals = [s for s in stack_lower if any(sig in s for sig in transactional_signals)]

    if scale_signals:
        return (
            "Likely strong fit. Their stack suggests growth and distributed workloads. "
            "TiDB can help with horizontal scaling, high availability, and handling both transactional and analytical queries."
        )

    if stack_items:
        return (
            "Possible fit. Their stack is not a direct signal of scaling pressure yet, "
            "but TiDB may still help if they have uptime goals, unpredictable traffic, or database consolidation needs."
        )

    return (
        "Unknown fit at this stage. More discovery is needed on performance bottlenecks, uptime requirements, "
        "global users, and data growth plans."
    )


def role_assessment(person_name: str, title_hint: str = "") -> str:
    t = title_hint.lower()
    if any(k in t for k in ["cto", "cio", "vp engineering", "head of engineering", "co-founder", "founder"]):
        return f"{person_name} is likely a **Decision Maker** (budget and final technical approval influence)."
    if any(k in t for k in ["architect", "engineering manager", "principal", "staff engineer", "lead"]):
        return f"{person_name} is likely a **Champion** (can advocate internally and shape technical requirements)."
    return f"{person_name} is likely a **Coach** until title/scope is confirmed on the call."


def build_questions(stack_items: List[str]) -> List[str]:
    base_questions = [
        "What database-related goals are most important this quarter (speed, uptime, cost, or developer productivity)?",
        "Where do you see the biggest friction today: slow queries, scaling risk, outages, or operational complexity?",
        "How quickly is your data volume and customer traffic growing?",
        "Are you planning any product launches, market expansions, or migrations in the next 6-12 months?",
        "What does a successful database project look like for your team and leadership?",
        "Who else is typically involved in database platform decisions?",
    ]

    if any("mysql" in s.lower() or "postgres" in s.lower() for s in stack_items):
        base_questions.append("Are you hitting limits with your current relational database during traffic spikes or peak business hours?")
    if any("kubernetes" in s.lower() or "microservices" in s.lower() for s in stack_items):
        base_questions.append("How much effort does your team spend keeping database operations stable across environments?")

    return base_questions


def create_markdown(inputs: ProspectInputs, website_data: dict, output_path: str) -> None:
    stack_items = parse_stack(inputs.tech_stack)
    fit_statement = fit_for_tidb(stack_items)
    host = urlparse(inputs.company_website).netloc if inputs.company_website else "Not provided"
    title_hint = ""

    lines = [
        f"# Discovery Brief: {inputs.company_name}",
        "",
        f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## 1) Background Information on the Person",
        f"- Name: {inputs.person_name or 'Not provided'}",
        f"- LinkedIn: {inputs.linkedin_profile or 'Not provided'}",
        "- Current Position: To be confirmed from LinkedIn during prep.",
        "- Previous Experience: Capture highlights from LinkedIn profile before the call.",
        "- Interests/Skills: Identify themes (data, scale, reliability, product velocity) from profile activity.",
        "",
        "## 2) Company Background",
        f"- Company Name: {inputs.company_name or 'Not provided'}",
        f"- Website: {inputs.company_website or 'Not provided'}",
        f"- Website Title: {website_data['title']}",
        f"- Website Summary: {website_data['description']}",
        f"- Visible Website Snippet: {website_data['snippet']}",
        f"- Domain: {host}",
        "- Industry: Confirm during discovery if not obvious from website.",
        "- Recent News: Add funding, product launches, hiring, or expansion updates before the call.",
        "",
        "## 3) Technology Stack Overview",
        f"- Existing Technologies: {', '.join(stack_items) if stack_items else 'Not provided'}",
        "- Data Maturity Snapshot:",
        "  - Early: single database, smaller team, limited data tooling.",
        "  - Growth: rising traffic, mixed workloads, reliability pressure.",
        "  - Scale: multiple services, strict uptime targets, operational overhead.",
        "",
        "## 4) Potential Pitfalls or Challenges",
        "- Rapid growth can stress traditional databases and cause performance incidents.",
        "- Complex infrastructure can increase operational burden on engineering teams.",
        "- Siloed data platforms can slow down reporting and cross-team decision making.",
        "- Cost unpredictability can become an issue as traffic and storage grow.",
        "",
        "## 5) Assessment of Fit for TiDB",
        f"- Fit Assessment: {fit_statement}",
        "- Why this matters to business stakeholders:",
        "  - Better uptime protects revenue and customer trust.",
        "  - Elastic scaling lowers launch risk during peak traffic.",
        "  - Unified transactional + analytical capabilities can simplify the data stack.",
        "",
        "## 6) Questions to Ask During the Call",
    ]

    for question in build_questions(stack_items):
        lines.append(f"- {question}")

    lines.extend(
        [
            "",
            "## 7) Role Assessment (Champion, Decision Maker, or Coach)",
            f"- {role_assessment(inputs.person_name or 'This contact', title_hint)}",
            "- Next step: confirm title, budget influence, and buying process in first 10 minutes.",
            "",
            "---",
            "",
            "### Internal Notes (for salesperson)",
            "- Keep language business-focused: outcomes over architecture details.",
            "- Tie every technical capability to a business risk or growth opportunity.",
            "- End the call with clear mutual action items and timeline.",
        ]
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a discovery-call prospecting brief in Markdown.")
    parser.add_argument("--company-name", required=True, help="Prospect company name")
    parser.add_argument("--person-name", required=True, help="Main contact full name")
    parser.add_argument("--linkedin-profile", required=True, help="LinkedIn profile URL")
    parser.add_argument("--company-website", required=True, help="Company website URL")
    parser.add_argument("--tech-stack", default="", help="Comma-separated technologies")
    parser.add_argument("--output", default="prospect_brief.md", help="Output markdown file path")
    parser.add_argument("--save-inputs-json", default="", help="Optional path to save raw inputs as JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    optional_deps_ready = ensure_dependencies()

    inputs = ProspectInputs(
        company_name=args.company_name,
        person_name=args.person_name,
        linkedin_profile=args.linkedin_profile,
        company_website=args.company_website,
        tech_stack=args.tech_stack,
    )

    website_data = fetch_website_summary(inputs.company_website, optional_deps_ready)
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    create_markdown(inputs, website_data, args.output)

    if args.save_inputs_json:
        json_output_dir = os.path.dirname(args.save_inputs_json)
        if json_output_dir:
            os.makedirs(json_output_dir, exist_ok=True)
        with open(args.save_inputs_json, "w", encoding="utf-8") as f:
            json.dump(inputs.__dict__, f, indent=2)

    print(f"[success] Brief created: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()

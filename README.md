# TiDB Prospecting Tool (Non-Technical Sales-Friendly)

This repository contains a simple command-line tool that prepares a discovery-call brief for a salesperson.

The tool generates a Markdown report with these sections:
1. Background Information on the Person
2. Company Background
3. Technology Stack Overview
4. Potential Pitfalls or Challenges
5. Assessment of Fit for TiDB
6. Questions to Ask During the Call
7. Role Assessment (Champion, Decision Maker, or Coach)

---

## 1) Prerequisites

- Python 3.9+
- Git

Check versions:

```bash
python3 --version
git --version
```

---

## 2) Install and Run

### Option A: browser-based frontend

Install dependencies and start the local server:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Then open:

```text
http://127.0.0.1:5000
```

Fill out the form, submit it, and the page will:
- generate the markdown brief under `output/`
- optionally save a JSON handoff file under `output/crm/`
- show the generated markdown in the browser

### Vercel deployment note

This repo includes a Vercel-ready Python entrypoint in `index.py`, static assets in `public/`, and a `vercel.json`
that bundles the Jinja templates. On Vercel, generated files are written to `/tmp/tidbproject-output`.

### Option A (Recommended): direct run with automatic dependency install

The script automatically checks whether required libraries are installed and installs missing ones.

```bash
python3 prospecting_tool.py \
  --company-name "Acme Corp" \
  --person-name "Jane Doe" \
  --linkedin-profile "https://www.linkedin.com/in/janedoe" \
  --company-website "https://example.com" \
  --tech-stack "MySQL, Kubernetes, AWS, Kafka" \
  --output "output/acme_discovery_brief.md"
```

### Option B: direct CLI run with explicit install first

```bash
python3 -m pip install -r requirements.txt
python3 prospecting_tool.py \
  --company-name "Acme Corp" \
  --person-name "Jane Doe" \
  --linkedin-profile "https://www.linkedin.com/in/janedoe" \
  --company-website "https://example.com" \
  --tech-stack "MySQL, Kubernetes, AWS, Kafka" \
  --output "output/acme_discovery_brief.md"
```

If the output folder does not exist, create it first:

```bash
mkdir -p output
```

---

## 3) Required Inputs

- `--company-name`: target company name
- `--person-name`: person you will meet
- `--linkedin-profile`: profile URL
- `--company-website`: company URL
- `--tech-stack`: comma-separated tools/platforms (optional but strongly recommended)

Optional:
- `--save-inputs-json`: stores the provided inputs for CRM handoff/audit
  - Nested output paths are supported and created automatically

---

## 4) What the Output Looks Like

The tool produces a Markdown file ready to share internally before the discovery call.

Example output file: `output/acme_discovery_brief.md`

Generated files under `output/` are ignored by git by default.

---

## 5) Push to GitHub (Step-by-Step)

After generating the brief and reviewing files:

```bash
git status
git add prospecting_tool.py requirements.txt README.md .gitignore

git commit -m "Add non-technical TiDB prospecting brief generator"
git push origin <your-branch-name>
```

If you need to create a new branch:

```bash
git checkout -b feat/prospecting-tool
git push -u origin feat/prospecting-tool
```

---

## 6) Sales Usage Tips

- Keep the conversation outcome-focused (risk, speed, cost, reliability).
- Ask open-ended discovery questions first; avoid pitching too early.
- Use the “Fit for TiDB” section to connect technical improvements to business impact.

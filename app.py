#!/usr/bin/env python3
"""Local web UI for the TiDB prospecting brief generator."""

from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory, url_for

from prospecting_tool import ProspectInputs, generate_brief


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

app = Flask(__name__)


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "prospect"


@app.route("/", methods=["GET", "POST"])
def index():
    form_data = {
        "company_name": "",
        "person_name": "",
        "linkedin_profile": "",
        "company_website": "",
        "tech_stack": "",
        "save_inputs_json": True,
    }
    result = None
    error = ""

    if request.method == "POST":
        form_data = {
            "company_name": request.form.get("company_name", "").strip(),
            "person_name": request.form.get("person_name", "").strip(),
            "linkedin_profile": request.form.get("linkedin_profile", "").strip(),
            "company_website": request.form.get("company_website", "").strip(),
            "tech_stack": request.form.get("tech_stack", "").strip(),
            "save_inputs_json": request.form.get("save_inputs_json") == "on",
        }

        missing = [
            label
            for label, value in (
                ("Company name", form_data["company_name"]),
                ("Person name", form_data["person_name"]),
                ("LinkedIn profile", form_data["linkedin_profile"]),
                ("Company website", form_data["company_website"]),
            )
            if not value
        ]

        if missing:
            error = f"Missing required fields: {', '.join(missing)}."
        else:
            inputs = ProspectInputs(
                company_name=form_data["company_name"],
                person_name=form_data["person_name"],
                linkedin_profile=form_data["linkedin_profile"],
                company_website=form_data["company_website"],
                tech_stack=form_data["tech_stack"],
            )
            slug = slugify(form_data["company_name"])
            brief_path = OUTPUT_DIR / f"{slug}_discovery_brief.md"
            inputs_path = OUTPUT_DIR / "crm" / f"{slug}_inputs.json"

            try:
                output_path = generate_brief(
                    inputs,
                    str(brief_path),
                    str(inputs_path) if form_data["save_inputs_json"] else "",
                )
                markdown = Path(output_path).read_text(encoding="utf-8")
                result = {
                    "markdown": markdown,
                    "brief_name": brief_path.name,
                    "brief_url": url_for("download_output", filename=brief_path.name),
                    "json_name": inputs_path.name if form_data["save_inputs_json"] else "",
                    "json_url": (
                        url_for("download_output", filename=f"crm/{inputs_path.name}")
                        if form_data["save_inputs_json"]
                        else ""
                    ),
                }
            except Exception as exc:  # noqa: BLE001
                error = f"Could not generate brief: {exc}"

    return render_template("index.html", form_data=form_data, result=result, error=error)


@app.route("/output/<path:filename>")
def download_output(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

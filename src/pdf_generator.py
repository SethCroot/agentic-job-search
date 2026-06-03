"""PDF generation for cover letters and resumes using weasyprint.

Ports the exact HTML/CSS design from generate_resume.js (agentic-job-search).
Design: Navy headers, Roboto font, clean professional A4 layout.
"""
import html as _html
import json as _json
from datetime import datetime
from pathlib import Path

from weasyprint import HTML

# ── Design tokens (from generate_resume.js) ──────────────────────────────────
NAVY = "#1a2b4a"
LIGHT_NAVY = "#e8ecf2"
TEXT = "#2c2c2c"
MUTED = "#555555"
ACCENT = "#4a6fa5"


def _esc(text: str) -> str:
    """HTML escape."""
    if not text:
        return ""
    return _html.escape(str(text))


# ── Resume CSS ────────────────────────────────────────────────────────────────
_RESUME_CSS = f"""
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Roboto', Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.45;
    color: {TEXT};
    background: #ffffff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}

  .header {{
    padding-bottom: 10px;
    margin-bottom: 13px;
    border-bottom: 2.5px solid {NAVY};
  }}
  .header-name {{
    font-size: 26pt;
    font-weight: 700;
    color: {NAVY};
    letter-spacing: -0.5px;
    line-height: 1;
    margin-bottom: 7px;
  }}
  .header-contact {{
    font-size: 8.5pt;
    color: {MUTED};
    display: flex;
    align-items: center;
    flex-wrap: wrap;
  }}
  .header-contact span {{ white-space: nowrap; }}
  .pipe {{ margin: 0 8px; color: #b0bccf; font-weight: 300; }}

  .section {{ margin-bottom: 15px; }}
  .section-title {{
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: {NAVY};
    border-left: 3px solid {NAVY};
    padding-left: 8px;
    margin-bottom: 10px;
    padding-bottom: 4px;
    border-bottom: 1px solid #e0e5ed;
  }}

  .summary-text {{ font-size: 9pt; line-height: 1.55; }}

  .skills-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 25px;
  }}
  .skill-group {{ font-size: 8.5pt; }}
  .skill-category {{
    font-weight: 700;
    color: {NAVY};
    margin-bottom: 4px;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  .role {{ padding-bottom: 9px; page-break-inside: avoid; }}
  .role + .role {{
    border-top: 1px solid #e4e9f0;
    padding-top: 9px;
  }}
  .role-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 3px;
  }}
  .role-left {{ flex: 1; padding-right: 12px; }}
  .role-title {{ font-weight: 700; font-size: 10pt; border-left: 3px solid {ACCENT}; padding-left: 6px; }}
  .role-company {{ font-size: 9pt; color: {MUTED}; }}
  .role-dates {{ font-size: 8pt; color: {MUTED}; white-space: nowrap; font-weight: 400; }}
  .role-overview {{
    font-size: 8.5pt;
    color: {MUTED};
    font-style: italic;
    margin: 3px 0 5px 8px;
    line-height: 1.4;
    padding-left: 8px;
    border-left: 2px solid #cdd5e0;
  }}

  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{
    font-size: 8.5pt;
    line-height: 1.45;
    margin-bottom: 2px;
    padding-left: 12px;
    position: relative;
  }}
  li::before {{ content: '\\2022'; position: absolute; left: 0; top: 0; color: {NAVY}; font-size: 7pt; }}

  .edu-item {{ margin-bottom: 5px; }}
  .references-text {{ font-size: 8.5pt; color: {MUTED}; font-style: italic; }}
"""

# ── Cover letter CSS ──────────────────────────────────────────────────────────
_COVER_CSS = f"""
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Roboto', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: {TEXT};
    background: #ffffff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}

  .header {{
    padding-bottom: 10px;
    margin-bottom: 24px;
    border-bottom: 2.5px solid {NAVY};
  }}
  .header-name {{
    font-size: 22pt;
    font-weight: 700;
    color: {NAVY};
    letter-spacing: -0.5px;
    line-height: 1;
    margin-bottom: 7px;
  }}
  .header-contact {{
    font-size: 8.5pt;
    color: {MUTED};
    display: flex;
    align-items: center;
    flex-wrap: wrap;
  }}
  .pipe {{ margin: 0 8px; color: #b0bccf; font-weight: 300; }}

  .date {{ font-size: 9.5pt; color: {MUTED}; margin-bottom: 20px; }}
  .salutation {{ font-size: 10.5pt; margin-bottom: 16px; color: {TEXT}; }}

  .body p {{
    font-size: 10.5pt;
    line-height: 1.65;
    color: {TEXT};
    margin-bottom: 14px;
    text-align: justify;
  }}

  .closing {{ margin-top: 24px; }}
  .closing p {{ font-size: 10.5pt; color: {TEXT}; line-height: 1.6; }}

  .signature {{ margin-top: 20px; }}
  .sig-name {{ font-size: 11pt; font-weight: 700; color: {NAVY}; margin-bottom: 3px; }}
  .sig-detail {{ font-size: 9pt; color: {MUTED}; }}
"""

# ── Google Fonts preload ─────────────────────────────────────────────────────
_FONTS_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,300;0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">'
)


# ──────────────────────────────────────────────────────────────────────────────
# Cover Letter PDF
# ──────────────────────────────────────────────────────────────────────────────

def generate_cover_letter_pdf(
    paragraphs: list[str],
    output_path: Path,
    name: str = "Seth Croot",
    location: str = "Vancouver, BC",
    email: str = "seth.croot@proton.me",
    phone: str = "",
    linkedin: str = "linkedin.com/in/seth-croot",
) -> Path:
    """Generate a cover letter PDF.

    Args:
        paragraphs: List of 3 strings [opening, fit, closing].
        output_path: Where to save the PDF.
        name: Full name for header + signature.
        location, email, phone, linkedin: Contact details.

    Returns:
        Path to the generated PDF.
    """
    today = datetime.now().strftime("%B %d, %Y")

    contact_parts = [f"<span>{_esc(location)}</span>"]
    if email:
        contact_parts.append(f'<span class="pipe">|</span><span>{_esc(email)}</span>')
    if phone:
        contact_parts.append(f'<span class="pipe">|</span><span>{_esc(phone)}</span>')
    if linkedin:
        contact_parts.append(
            f'<span class="pipe">|</span><span>'
            f'<a href="https://{_esc(linkedin)}" style="color:{MUTED};text-decoration:none;">{_esc(linkedin)}</a>'
            f'</span>'
        )

    body_html = "\n".join(f"  <p>{_esc(p)}</p>" for p in paragraphs)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{_FONTS_LINK}
<style>{_COVER_CSS}</style>
</head>
<body>

<div class="header">
  <div class="header-name">{_esc(name)}</div>
  <div class="header-contact">
    {"".join(contact_parts)}
  </div>
</div>

<p class="date">{today}</p>

<p class="salutation">Dear Hiring Manager,</p>

<div class="body">
{body_html}
</div>

<div class="closing">
  <p>Yours sincerely,</p>
</div>

<div class="signature">
  <p class="sig-name">{_esc(name)}</p>
  <p class="sig-detail">{_esc(email)}</p>
  {f'<p class="sig-detail">{_esc(linkedin)}</p>' if linkedin else ''}
</div>

</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content).write_pdf(output_path)
    return output_path


# ──────────────────────────────────────────────────────────────────────────────
# Resume PDF
# ──────────────────────────────────────────────────────────────────────────────

def generate_resume_pdf(
    resume_data: dict,
    output_path: Path,
    name: str = "Seth Croot",
    location: str = "Vancouver, BC",
    email: str = "seth.croot@proton.me",
    phone: str = "",
    linkedin: str = "linkedin.com/in/seth-croot",
) -> Path:
    """Generate a resume PDF from resume_facts.yaml data.

    Args:
        resume_data: Dict from resume_facts.yaml (loaded via config).
        output_path: Where to save the PDF.
        name, location, email, phone, linkedin: Contact details.

    Returns:
        Path to the generated PDF.
    """
    contact_parts = [f"<span>{_esc(location)}</span>"]
    if email:
        contact_parts.append(f'<span class="pipe">|</span><span>{_esc(email)}</span>')
    if phone:
        contact_parts.append(f'<span class="pipe">|</span><span>{_esc(phone)}</span>')
    if linkedin:
        contact_parts.append(
            f'<span class="pipe">|</span><span>'
            f'<a href="https://{_esc(linkedin)}" style="color:{MUTED};text-decoration:none;">{_esc(linkedin)}</a>'
            f'</span>'
        )

    # Summary
    summary = resume_data.get("summary", "")
    summary_html = f'<p class="summary-text">{_esc(summary)}</p>'

    # Skills
    skills = resume_data.get("skills", {})
    skill_groups = []
    for category, items in skills.items():
        if category == "certifications":
            continue  # Certs go in education section
        label = category.replace("_", " ").title()
        items_html = "".join(f"<li>{_esc(i)}</li>" for i in items)
        skill_groups.append(
            f'<div class="skill-group">\n'
            f'  <p class="skill-category">{_esc(label)}</p>\n'
            f'  <ul>{items_html}</ul>\n'
            f'</div>'
        )
    skills_html = f'<div class="skills-grid">{"".join(skill_groups)}</div>'

    # Experience
    experience = resume_data.get("experience", [])
    roles_html = []
    for role in experience:
        bullets_html = "".join(f"<li>{_esc(b)}</li>" for b in role.get("bullets", []))
        roles_html.append(
            f'<div class="role">\n'
            f'  <div class="role-header">\n'
            f'    <div class="role-left">\n'
            f'      <span class="role-title">{_esc(role.get("title", ""))}</span>\n'
            f'      <span class="role-company"> &nbsp;&middot;&nbsp; '
            f'{_esc(role.get("company", ""))}, {_esc(role.get("location", ""))}</span>\n'
            f'    </div>\n'
            f'    <span class="role-dates">{_esc(role.get("dates", ""))}</span>\n'
            f'  </div>\n'
            f'  <ul>{bullets_html}</ul>\n'
            f'</div>'
        )
    experience_html = "".join(roles_html)

    # Education
    education = resume_data.get("education", [])
    # Also include certifications
    certs = skills.get("certifications", [])
    edu_items = []
    for edu in education:
        edu_items.append(
            f'<div class="edu-item">\n'
            f'  <div class="role-header">\n'
            f'    <div class="role-left">\n'
            f'      <span class="role-title">{_esc(edu.get("degree", ""))}</span>\n'
            f'      <span class="role-company"> &nbsp;&middot;&nbsp; {_esc(edu.get("institution", ""))}</span>\n'
            f'    </div>\n'
            f'    <span class="role-dates">{_esc(edu.get("year", ""))}</span>\n'
            f'  </div>\n'
            f'</div>'
        )
    for cert in certs:
        edu_items.append(
            f'<div class="edu-item">\n'
            f'  <div class="role-header">\n'
            f'    <div class="role-left">\n'
            f'      <span class="role-title">{_esc(cert)}</span>\n'
            f'    </div>\n'
            f'  </div>\n'
            f'</div>'
        )
    education_html = "".join(edu_items)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
{_FONTS_LINK}
<style>{_RESUME_CSS}</style>
</head>
<body>

<div class="header">
  <div class="header-name">{_esc(name)}</div>
  <div class="header-contact">
    {"".join(contact_parts)}
  </div>
</div>

<div class="section">
  <div class="section-title">Summary</div>
  {summary_html}
</div>

<div class="section">
  <div class="section-title">Key Skills</div>
  {skills_html}
</div>

<div class="section">
  <div class="section-title">Career History</div>
  {experience_html}
</div>

<div class="section">
  <div class="section-title">Education &amp; Certifications</div>
  {education_html}
</div>

<div class="section">
  <div class="section-title">References</div>
  <p class="references-text">Available upon request</p>
</div>

</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content).write_pdf(output_path)
    return output_path

"""Generate cover letter PDF + resume PDF for a specific job.

Usage:
  python3 -m src.apply --job "Aritzia - IT Support Specialist"
  python3 -m src.apply --job "Aritzia" --cover-letter-only
  python3 -m src.apply --job "Aritzia" --resume-only

Outputs to vault: 06-Career/Jobs/Company/Role/SethCroot_CoverLetter.pdf
                                       SethCroot_Resume.pdf
                                       job.md
"""
import argparse
import json as _json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.config import Config
from src.tailoring import TailoringEngine
from src.cover_letter import CoverLetterGenerator
from src.pdf_generator import generate_cover_letter_pdf, generate_resume_pdf


# ── Contact info ──────────────────────────────────────────────────────────────
CONTACT = {
    "name": "Seth Croot",
    "location": "Vancouver, BC",
    "email": "seth.croot@proton.me",
    "phone": "",
    "linkedin": "linkedin.com/in/seth-croot",
}


def find_job_file(jobs_dir: Path, query: str) -> list[Path]:
    """Find job files by partial company or title match."""
    query_lower = query.lower()
    candidates = []
    for f in jobs_dir.glob("*.md"):
        if query_lower in f.name.lower():
            candidates.append(f)
    # Also check subdirectories (new structure)
    for f in jobs_dir.rglob("job.md"):
        parent = f.parent
        if query_lower in parent.name.lower() or query_lower in parent.parent.name.lower():
            candidates.append(f)
    return candidates


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text = parts[1].strip()
    body = parts[2].strip()

    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            fm[key.strip()] = val
    return fm, body


def get_output_dir(jobs_dir: Path, company: str, title: str) -> Path:
    """Get the output directory: 06-Career/Jobs/Company/Title/"""
    safe_company = re.sub(r'[/\\:*?"<>|]', ' ', company).strip()
    safe_title = re.sub(r'[/\\:*?"<>|]', ' ', title).strip()
    output_dir = jobs_dir / safe_company / safe_title
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def apply_for_job(
    job_file: Path,
    config: Config,
    cover_letter_only: bool = False,
    resume_only: bool = False,
) -> dict:
    """Generate application materials for a single job."""
    content = job_file.read_text()
    fm, body = parse_frontmatter(content)

    company = fm.get("company", "Unknown")
    title = fm.get("role", job_file.stem)
    jobs_dir = config.jobs_dir

    print(f"\n{'='*50}")
    print(f"Processing: {title} at {company}")
    print(f"{'='*50}")

    # Extract job description from body
    desc_match = re.search(r"## Description\n(.+?)(?:\n##|\Z)", body, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    job = {
        "title": title,
        "company": company,
        "location": fm.get("location", "N/A"),
        "description": description,
        "job_url": fm.get("url", ""),
    }

    output_dir = get_output_dir(jobs_dir, company, title)
    results = {"company": company, "title": title, "output_dir": str(output_dir)}

    # Step 1: Generate tailoring (needed for cover letter too)
    tailoring = None
    if not cover_letter_only:
        print(f"[1/2] Generating tailored resume highlights...")
        tailor = TailoringEngine(config)
        tailoring = tailor.tailor_for_job(job)
        if "error" in tailoring:
            print(f"  ✗ Tailoring failed: {tailoring['error']}")
            results["tailoring_error"] = tailoring["error"]
        else:
            print(f"  ✓ Summary: {tailoring.get('summary', 'N/A')[:80]}...")
            print(f"  ✓ Skills: {', '.join(tailoring.get('highlighted_skills', [])[:5])}")
            if tailoring.get("skill_gaps"):
                print(f"  ⚠ Gaps: {', '.join(tailoring['skill_gaps'][:3])}")
            results["tailoring"] = tailoring

    # Step 2: Generate cover letter PDF
    if not resume_only:
        print(f"[2/2] Generating cover letter...")
        cl = CoverLetterGenerator(config)
        if tailoring is None:
            tailor = TailoringEngine(config)
            tailoring = tailor.tailor_for_job(job)

        cl_data = cl.generate(job, tailoring)
        if cl_data.get("error"):
            print(f"  ✗ Cover letter failed: {cl_data['error']}")
            results["cover_letter_error"] = cl_data["error"]
        else:
            paragraphs = [cl_data["opening"], cl_data["fit"], cl_data["closing"]]
            cl_path = output_dir / "SethCroot_Cover Letter.pdf"
            generate_cover_letter_pdf(
                paragraphs=paragraphs,
                output_path=cl_path,
                **CONTACT,
            )
            print(f"  ✓ Cover letter PDF: {cl_path.name}")
            results["cover_letter_path"] = str(cl_path)

    # Step 3: Generate resume PDF
    if not cover_letter_only and tailoring and "error" not in tailoring:
        print(f"[3/3] Generating resume PDF...")
        resume_path = output_dir / "SethCroot_Resume.pdf"
        resume_data = config.resume_facts

        # Apply tailoring: reorder bullets based on relevance
        if tailoring.get("highlighted_experience"):
            highlighted_bullets = [
                h["bullet"] for h in tailoring["highlighted_experience"]
                if "bullet" in h
            ]
            # Move highlighted bullets to the top of the first role's bullets
            for role in resume_data.get("experience", []):
                existing = role.get("bullets", [])
                reordered = [b for b in highlighted_bullets if b in existing]
                remaining = [b for b in existing if b not in reordered]
                role["bullets"] = reordered + remaining

        # Apply tailored summary
        if tailoring.get("summary"):
            resume_data["summary"] = tailoring["summary"]

        generate_resume_pdf(
            resume_data=resume_data,
            output_path=resume_path,
            **CONTACT,
        )
        print(f"  ✓ Resume PDF: {resume_path.name}")
        results["resume_path"] = str(resume_path)

    # Step 4: Update job.md in the subdirectory
    job_md_path = output_dir / "job.md"
    
    # Read existing content (file should already be in the subdirectory)
    if job_md_path.exists():
        md_content = job_md_path.read_text()
    elif job_file != job_md_path:
        md_content = content
    else:
        md_content = content

    # Update frontmatter
    updates = {
        "cover_letter_status": "Generated",
        "status": "Applying",
    }
    if results.get("cover_letter_path"):
        updates["cover_letter_path"] = results["cover_letter_path"]
    if results.get("resume_path"):
        updates["resume_path"] = results["resume_path"]

    for key, value in updates.items():
        pattern = rf"^{re.escape(key)}:.*$"
        new_line = f"{key}: {value}"
        if re.search(pattern, md_content, re.MULTILINE):
            md_content = re.sub(pattern, new_line, md_content, flags=re.MULTILINE)
        else:
            # Add before closing --- of frontmatter
            md_content = md_content.replace("---\n\n", f"{new_line}\n---\n\n", 1)

    # Add PDF links section
    pdf_links = "\n## Application Materials\n"
    if results.get("cover_letter_path"):
        pdf_links += "- [[SethCroot_Cover Letter.pdf|Cover Letter]]\n"
    if results.get("resume_path"):
        pdf_links += "- [[SethCroot_Resume.pdf|Resume]]\n"

    if "## Application Materials" not in md_content:
        md_content += pdf_links

    job_md_path.write_text(md_content)
    print(f"  ✓ Job file updated: {job_md_path.relative_to(jobs_dir)}")

    results["success"] = True
    return results


def main():
    parser = argparse.ArgumentParser(description="Generate application materials for scored jobs")
    parser.add_argument("--job", required=True, help="Job name to search for (company or title)")
    parser.add_argument("--cover-letter-only", action="store_true", help="Only generate cover letter")
    parser.add_argument("--resume-only", action="store_true", help="Only generate tailoring + resume")
    args = parser.parse_args()

    config = Config()
    jobs_dir = config.jobs_dir

    print(f"Searching for job matching: '{args.job}'")
    candidates = find_job_file(jobs_dir, args.job)

    if not candidates:
        print(f"✗ No job file found matching '{args.job}'")
        print(f"  Available jobs in {jobs_dir}:")
        for f in sorted(jobs_dir.glob("*.md"))[:20]:
            print(f"  - {f.stem}")
        sys.exit(1)

    if len(candidates) > 1:
        print(f"[!] Multiple matches for '{args.job}':")
        for i, f in enumerate(candidates, 1):
            print(f"  {i}. {f.name}")
        # Use first match
        print(f"  Using: {candidates[0].name}")

    result = apply_for_job(
        candidates[0], config,
        cover_letter_only=args.cover_letter_only,
        resume_only=args.resume_only,
    )

    print(f"\n{'='*50}")
    print(f"DONE — {result['title']} at {result['company']}")
    print(f"Output: {result.get('output_dir', 'N/A')}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

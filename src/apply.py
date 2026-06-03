"""Generate cover letter + tailored resume for a specific job.

Usage:
  python3 -m src.apply --job "Aritzia - IT Support Specialist"
  python3 -m src.apply --job "Aritzia" --cover-letter-only
  python3 -m src.apply --job "Aritzia" --resume-only
  python3 -m src.apply --all-passing  # process all jobs with status: Scored

Reads job from vault (06-Career/Jobs/), generates outputs,
writes to local files (Google Drive upload coming in Phase D).
Updates vault file with links/status.
"""
import argparse
import json as _json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.config import Config
from src.tailoring import TailoringEngine
from src.cover_letter import CoverLetterGenerator


def find_job_file(jobs_dir: Path, query: str) -> Path | None:
    """Find a job file by partial company or title match."""
    query_lower = query.lower()
    candidates = []
    for f in jobs_dir.glob("*.md"):
        if query_lower in f.name.lower():
            candidates.append(f)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        print(f"[!] Multiple matches for '{query}':")
        for i, f in enumerate(candidates, 1):
            print(f"  {i}. {f.name}")
        return None
    return None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_text = parts[1].strip()
    body = parts[2].strip()
    
    # Simple YAML parser for flat key: value pairs
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            fm[key.strip()] = val
    return fm, body


def update_vault_file(filepath: Path, fm: dict, updates: dict) -> None:
    """Update frontmatter fields in a vault file."""
    content = filepath.read_text()
    
    for key, value in updates.items():
        # Replace or add frontmatter field
        pattern = rf"^{key}:.*$"
        new_line = f"{key}: {value}"
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
        else:
            # Add before closing ---
            content = content.replace("---\n\n", f"{new_line}\n---\n\n", 1)
    
    filepath.write_text(content)


def apply_for_job(
    job_file: Path,
    config: Config,
    cover_letter_only: bool = False,
    resume_only: bool = False,
) -> dict:
    """Generate application materials for a single job."""
    content = job_file.read_text()
    fm, body = parse_frontmatter(content)
    
    company = fm.get("company", fm.get("role", "Unknown").split(" at ")[-1] if " at " in fm.get("role", "") else "Unknown")
    title = fm.get("role", job_file.stem)
    
    print(f"\n{'='*50}")
    print(f"Processing: {title} at {company}")
    print(f"File: {job_file.name}")
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
    
    results = {"job_file": str(job_file), "company": company, "title": title}
    
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
            print(f"  ✓ Skills highlighted: {', '.join(tailoring.get('highlighted_skills', [])[:5])}")
            if tailoring.get("skill_gaps"):
                print(f"  ⚠ Skill gaps: {', '.join(tailoring['skill_gaps'][:3])}")
            results["tailoring"] = tailoring
    
    # Step 2: Generate cover letter
    if not resume_only:
        print(f"[2/2] Generating cover letter...")
        cl = CoverLetterGenerator(config)
        if tailoring is None:
            # Generate basic tailoring for cover letter context
            tailor = TailoringEngine(config)
            tailoring = tailor.tailor_for_job(job)
        
        cover_letter = cl.generate(job, tailoring)
        if cover_letter.startswith("Error"):
            print(f"  ✗ Cover letter failed: {cover_letter}")
            results["cover_letter_error"] = cover_letter
        else:
            print(f"  ✓ Cover letter generated ({len(cover_letter)} chars)")
            results["cover_letter"] = cover_letter
    
    # Step 3: Write outputs to local files
    # Output dir: /opt/data/seth-jobsearch-auto/output/
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    safe_name = re.sub(r'[/\\:*?"<>|]', '-', f"{company} - {title}")
    timestamp = datetime.now().strftime('%Y%m%d')
    
    if "tailoring" in results:
        tailoring_path = output_dir / f"{timestamp} - {safe_name} - Tailoring.json"
        tailoring_path.write_text(_json.dumps(results["tailoring"], indent=2))
        results["tailoring_path"] = str(tailoring_path)
        print(f"  → Tailoring saved: {tailoring_path.name}")
    
    if "cover_letter" in results:
        cl_path = output_dir / f"{timestamp} - {safe_name} - Cover Letter.txt"
        cl_path.write_text(results["cover_letter"])
        results["cover_letter_path"] = str(cl_path)
        print(f"  → Cover letter saved: {cl_path.name}")
    
    # Step 4: Update vault file
    vault_updates = {
        "cover_letter_status": "Generated",
    }
    if "cover_letter_path" in results:
        vault_updates["cover_letter_path"] = results["cover_letter_path"]
    if "tailoring_path" in results:
        vault_updates["tailoring_path"] = results["tailoring_path"]
    
    update_vault_file(job_file, fm, vault_updates)
    print(f"  → Vault file updated")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Generate application materials for scored jobs")
    parser.add_argument("--job", required=True, help="Job name to search for (company or title)")
    parser.add_argument("--cover-letter-only", action="store_true", help="Only generate cover letter")
    parser.add_argument("--resume-only", action="store_true", help="Only generate tailoring")
    args = parser.parse_args()
    
    config = Config()
    jobs_dir = config.jobs_dir
    
    print(f"Searching for job matching: '{args.job}'")
    job_file = find_job_file(jobs_dir, args.job)
    
    if job_file is None:
        print(f"✗ No job file found matching '{args.job}'")
        print(f"  Available jobs in {jobs_dir}:")
        for f in sorted(jobs_dir.glob("*.md"))[:20]:
            print(f"  - {f.stem}")
        sys.exit(1)
    
    result = apply_for_job(
        job_file, config,
        cover_letter_only=args.cover_letter_only,
        resume_only=args.resume_only,
    )
    
    print(f"\n{'='*50}")
    print(f"DONE — {result['title']} at {result['company']}")
    if result.get("cover_letter_path"):
        print(f"Cover letter: {result['cover_letter_path']}")
    if result.get("tailoring_path"):
        print(f"Tailoring: {result['tailoring_path']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

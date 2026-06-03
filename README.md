# Agentic Job Search

Automated job discovery, scoring, and application pipeline — built to run as a daily cron job via [Hermes Agent](https://github.com/nousresearch/hermes-agent).

Discovers jobs from LinkedIn and Indeed, scores them with AI, generates tailored cover letters and resumes as PDFs, and tracks everything in an Obsidian vault.

## Pipeline Flow

```
Daily Cron (06:00 PT)
  │
  ├─ 1. Discover ──── JobSpy scrapes LinkedIn + Indeed (7 searches)
  ├─ 2. Dedup ──────── Persistent seen_jobs.csv (survives vault deletes)
  ├─ 3. Pre-filter ──── Title + location keywords (rejects irrelevant roles)
  ├─ 4. Score ──────── GLM-4.7 via Z.ai coding plan (1-10 scale)
  └─ 5. Write ──────── Scored jobs → Obsidian Inbox → routed to Jobs folder

On-demand (via Discord: "apply for X job")
  │
  ├─ Generate tailoring (AI highlights relevant experience)
  ├─ Generate cover letter PDF (3-paragraph, follows configurable rules)
  └─ Generate resume PDF (tailored bullet ordering + summary)
```

## Output Structure

```
Obsidian Vault/06-Career/Jobs/
  Company Name/
    Job Title/
      job.md                      ← score, description, tailoring, status
      SethCroot_Cover Letter.pdf  ← generated on apply
      SethCroot_Resume.pdf        ← generated on apply
```

## PDF Design

Professional A4 PDFs with navy headers, Roboto font, clean layout — CSS ported from the original `generate_resume.js`. Cover letters follow a strict ruleset (`rules/cover_letter_rules.md`) that bans generic phrases and enforces specificity.

## Tech Stack

- **Job discovery:** [python-jobspy](https://github.com/BunsenStrike/python-jobspy) (LinkedIn + Indeed)
- **AI scoring + generation:** Z.ai GLM-4.7 (OpenAI-compatible API)
- **PDF generation:** [WeasyPrint](https://weasyprint.org/) (HTML/CSS → PDF)
- **Vault integration:** Obsidian markdown with YAML frontmatter
- **Scheduling:** Hermes cron jobs (daily discovery + inbox processing)
- **Notifications:** Discord via Hermes

## Requirements

- Python 3.12+
- [Hermes Agent](https://github.com/nousresearch/hermes-agent) (for cron + Discord)
- Z.ai API key (coding plan)
- Obsidian vault (mounted at `/vault`)

## Configuration

All config lives in `config/`:

| File | Purpose |
|------|---------|
| `ai.yaml` | API key, model, base URL |
| `searches.yaml` | Job search queries, sites, locations |
| `scoring_rules.yaml` | Threshold, criteria weights |
| `profile.yaml` | Job preferences (role types, locations) |
| `resume_facts.yaml` | Verified career data for AI generation |
| `employers.yaml` | Target employer list |
| `employers_sites.yaml` | Target employer career page URLs |

## Setup

```bash
git clone https://github.com/SethCroot/agentic-job-search.git
cd agentic-jobsearch-auto

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API key and vault path

# Test
python3 -m src.main --discover-only --no-discord --verbose --limit 3
```

## CLI Usage

```bash
# Discover jobs only (no scoring)
python3 -m src.main --discover-only --no-discord --verbose

# Full pipeline (discover + score)
python3 -m src.main --score-only --no-discord --verbose --limit 30

# Generate application materials for a specific job
python3 -m src.apply --job "Company Name"
python3 -m src.apply --job "Company Name" --cover-letter-only
```

## License

MIT

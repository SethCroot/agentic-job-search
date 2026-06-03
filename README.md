# Seth JobSearch Auto

> AI-powered job discovery and application preparation for Vancouver IT roles

## Overview

Automated job search system that discovers, scores, and prepares application materials for IT roles in Vancouver's retail industry.

## Tech Stack

- **Base**: Fork of Pickle-Pixel/ApplyPilot (AGPL-3.0)
- **Runtime**: Python 3.11+
- **AI**: Z.ai GLM-4.7 (scoring, tailoring, cover letters)
- **Job Discovery**: JobSpy (LinkedIn, Glassdoor, Indeed, Google Jobs)
- **Data Storage**: Obsidian vault (JSON database + dashboard)

## Project Structure

```
seth-jobsearch-auto/
├── config/           # Configuration files (YAML)
├── src/              # Source code
├── tests/            # Unit and integration tests
├── docs/             # Documentation
└── README.md         # This file
```

## Setup

1. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure API keys:
   ```bash
   pass show services/zai/api-key > config/.zai_api_key
   ```

4. Run:
   ```bash
   python src/main.py
   ```

## Configuration

See `config/` directory for:
- `profile.yaml` - Personal profile
- `resume_facts.yaml` - Resume facts (no fabrication)
- `searches.yaml` - Job search queries
- `scoring_rules.yaml` - Scoring criteria
- `employers.yaml` - Target employers
- `ai.yaml` - Z.ai configuration

## License

AGPL-3.0 (fork of ApplyPilot)

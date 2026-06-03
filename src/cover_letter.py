"""Cover letter generation using GLM-4.7.

Follows rules from rules/cover_letter_rules.md:
- 3 paragraphs (opening, fit, closing), 150-200 words total
- No specific tech names — conceptual references only
- No banned phrases
- Outputs structured JSON: {opening, fit, closing}
"""
import json
from pathlib import Path
from openai import OpenAI
from .config import Config


class CoverLetterGenerator:
    """Generate 3-paragraph cover letters following the rules."""

    # Load rules once
    _RULES_PATH = Path(__file__).parent.parent / "rules" / "cover_letter_rules.md"

    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.ai.get("api_key", ""),
            base_url=config.ai.get("base_url", "https://open.bigmodel.cn/api/coding/paas/v4"),
        )
        self.timeout = 60.0  # GLM-4.7 can be slow
        self.model = config.ai.get("model", "glm-4.7")

        # Load rules
        if self._RULES_PATH.exists():
            self.rules = self._RULES_PATH.read_text()
        else:
            self.rules = "Follow standard professional cover letter conventions."

    def generate(self, job: dict, tailoring: dict) -> dict:
        """Generate a 3-paragraph cover letter.

        Returns:
            dict with keys: opening, fit, closing (each a string)
            On error: dict with key 'error' set
        """
        facts = self.config.resume_facts
        name = facts.get("personal", {}).get("name", "Seth Croot")

        prompt = f"""Write a professional 3-paragraph cover letter.

CANDIDATE: {name}
VERIFIED FACTS (use ONLY these): {json.dumps(facts, indent=2)}

JOB:
- Title: {job.get('title', 'N/A')}
- Company: {job.get('company', 'N/A')}
- Location: {job.get('location', 'N/A')}
- Description: {str(job.get('description', 'N/A'))[:1500]}

TAILORED HIGHLIGHTS: {json.dumps(tailoring, indent=2)}

COVER LETTER RULES (MUST follow all of these):
{self.rules}

Respond with ONLY valid JSON — no other text:
{{
  "opening": "<paragraph 1 — 2-3 sentences, reference something specific about the company>",
  "fit": "<paragraph 2 — 3-4 sentences, describe what candidate has done, no tech names>",
  "closing": "<paragraph 3 — availability + direct closing>"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=800,
                timeout=self.timeout,
            )
            text = response.choices[0].message.content.strip()

            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            result = json.loads(text)
            return result

        except json.JSONDecodeError as e:
            import re
            json_match = re.search(r'\{[\s\S]*\}', text if 'text' in dir() else '')
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return {"error": f"JSON parse failed: {e}", "opening": "", "fit": "", "closing": ""}
        except Exception as e:
            return {"error": str(e), "opening": "", "fit": "", "closing": ""}

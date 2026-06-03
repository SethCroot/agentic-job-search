"""Resume tailoring engine - NO FABRICATION permitted."""
import json
from openai import OpenAI
from ..config import Config


class TailoringEngine:
    """Tailor resume for specific jobs using only verified facts."""
    
    FABRICATION_GUARD = """CRITICAL RULE: You may ONLY use information from the resume_facts provided below.
You may reorder, emphasize, or de-emphasize existing facts. You may NOT:
- Invent new skills not listed
- Fabricate experience or achievements
- Add certifications not present
- Create new job responsibilities
- Make up any information whatsoever

If the job requires skills not in the facts, note them as gaps, do not fake them."""

    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.ai.get("api_key", ""),
            base_url=config.ai.get("base_url", "https://open.bigmodel.cn/api/coding/paas/v4"),
        )
        self.timeout = 30.0  # Default timeout for API calls
        self.model = config.ai.get("model", "glm-4.7")
    
    def tailor_for_job(self, job: dict) -> dict:
        """Generate a tailored resume for a specific job."""
        facts = self.config.resume_facts
        
        prompt = f"""{self.FABRICATION_GUARD}

JOB POSTING:
- Title: {job.get('title', 'N/A')}
- Company: {job.get('company', 'N/A')}
- Description: {str(job.get('description', 'N/A'))[:2000]}

CANDIDATE VERIFIED FACTS:
{json.dumps(facts, indent=2)}

Task: Reorder and emphasize the candidate's verified experience and skills to best match this job.
Highlight the most relevant 3-5 experience bullets and 5-8 skills.

Respond with ONLY valid JSON:
{{
  "summary": "<tailored 2-sentence summary using only verified facts>",
  "highlighted_experience": [
    {{"bullet": "<verbatim from facts>", "relevance": "<why relevant>"}}
  ],
  "highlighted_skills": ["<skills from facts list>"],
  "skill_gaps": ["<skills job requires but candidate lacks>"],
  "tailoring_notes": "<what was reordered/emphasized and why>"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500,
                timeout=self.timeout,
            )
            
            text = response.choices[0].message.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            return json.loads(text)
        except Exception as e:
            return {"error": str(e), "summary": "", "highlighted_experience": [], "highlighted_skills": []}

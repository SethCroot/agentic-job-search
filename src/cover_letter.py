"""Cover letter generation using GLM-4.7."""
import json
from openai import OpenAI
from .config import Config


class CoverLetterGenerator:
    """Generate 3-paragraph cover letters."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.ai.get("api_key", ""),
            base_url=config.ai.get("base_url", "https://open.bigmodel.cn/api/coding/paas/v4"),
        )
        self.timeout = 60.0  # GLM-4.7 can be slow
        self.model = config.ai.get("model", "glm-4.7")
    
    def generate(self, job: dict, tailoring: dict) -> str:
        """Generate a 3-paragraph cover letter."""
        facts = self.config.resume_facts
        name = facts.get("personal", {}).get("name", "Seth Croot")
        
        prompt = f"""Write a professional 3-paragraph cover letter.

CANDIDATE: {name}
VERIFIED FACTS (use ONLY these): {json.dumps(facts, indent=2)}

JOB:
- Title: {job.get('title', 'N/A')}
- Company: {job.get('company', 'N/A')}
- Description: {str(job.get('description', 'N/A'))[:1500]}

TAILORED HIGHLIGHTS: {json.dumps(tailoring, indent=2)}

Structure:
- Paragraph 1: Opening — role applied for, why this company specifically
- Paragraph 2: Fit — relevant experience and skills (VERIFIED FACTS ONLY)
- Paragraph 3: Closing — enthusiasm, availability, call to action

Keep it concise, professional, and factual. No embellishment."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=800,
                timeout=self.timeout,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating cover letter: {e}"

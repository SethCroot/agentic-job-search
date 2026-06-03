"""Configuration loader for Seth JobSearch Auto."""
import os
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"


def load_yaml(filename: str) -> dict:
    """Load a YAML config file."""
    path = CONFIG_DIR / filename
    with open(path) as f:
        return yaml.safe_load(f) or {}


class Config:
    """Central configuration."""
    
    def __init__(self):
        self.ai = load_yaml("ai.yaml")
        self.employers = load_yaml("employers.yaml")
        self.scoring_rules = load_yaml("scoring_rules.yaml")
        self.searches = load_yaml("searches.yaml")
        self.profile = load_yaml("profile.yaml")
        self.resume_facts = load_yaml("resume_facts.yaml")
        
        # Resolve API key from env
        env_var = self.ai.get("api_key_env", "GLM_API_KEY")
        self.ai["api_key"] = os.environ.get(env_var, "")
        
        # Vault path
        self.vault_path = Path(os.environ.get(
            "VAULT_PATH", "/vault"
        ))
        self.jobs_dir = self.vault_path / "06-Career" / "Jobs"
        self.daily_dir = self.vault_path / "01-Daily"
    
    def get_employer_names(self) -> list[str]:
        return [e["name"] for e in self.employers.get("employers", [])]

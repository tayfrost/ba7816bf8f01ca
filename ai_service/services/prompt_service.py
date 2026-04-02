"""Service for loading and managing versioned system prompts."""

import os
import logging
from pathlib import Path
from typing import Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptService:
    """Service for loading and managing system prompts with versioning support."""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
    
    def _parse_version(self, filename: str) -> tuple:
        """Extract version tuple from filename like 'system_prompt_v1.0.0.txt'."""
        match = re.search(r'v(\d+)\.(\d+)\.(\d+)', filename)
        if match:
            return tuple(map(int, match.groups()))
        return (0, 0, 0)
    
    def get_latest_version(self, prompt_prefix: str = "system_prompt", subfolder: Optional[str] = None) -> Optional[str]:
        """Find the latest version of a prompt by prefix."""
        search_dir = self.prompts_dir / subfolder if subfolder else self.prompts_dir
        
        if not search_dir.exists():
            logger.error(f"Directory does not exist: {search_dir}")
            return None
        
        # If in subfolder and no specific prefix, find any versioned prompt
        if subfolder and prompt_prefix == "system_prompt":
            prompt_files = [
                f for f in search_dir.iterdir()
                if f.is_file() and re.search(r'v\d+\.\d+\.\d+', f.name)
            ]
        else:
            prompt_files = [
                f for f in search_dir.iterdir()
                if f.is_file() and f.name.startswith(prompt_prefix)
            ]
        
        if not prompt_files:
            logger.error(f"No prompt files found in {search_dir} (prefix: {prompt_prefix})")
            return None
        
        latest = max(prompt_files, key=lambda f: self._parse_version(f.name))
        logger.info(f"Loaded prompt: {latest.name} from {search_dir}")
        return latest.name
    
    def load_prompt(self, filename: Optional[str] = None, subfolder: Optional[str] = None) -> str:
        """Load a specific prompt or the latest version from optional subfolder."""
        search_dir = self.prompts_dir / subfolder if subfolder else self.prompts_dir
        logger.info(f"Loading prompt from: {search_dir}")
        
        if filename is None:
            filename = self.get_latest_version(subfolder=subfolder)
            if filename is None:
                logger.error(f"No prompts found in {search_dir}")
                raise FileNotFoundError(f"No prompts found in {search_dir}")
        
        prompt_path = search_dir / filename
        if not prompt_path.exists():
            logger.error(f"Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        logger.info(f"Successfully loaded: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")
    
    def load_prompt_by_version(self, version: str, prompt_prefix: str = "system_prompt") -> str:
        """Load a specific version of a prompt (e.g., '1.0.0')."""
        filename = f"{prompt_prefix}_v{version}.txt"
        return self.load_prompt(filename)
    
    def list_available_prompts(self) -> list:
        """List all available prompts with their versions."""
        if not self.prompts_dir.exists():
            return []
        
        prompts = []
        for f in self.prompts_dir.iterdir():
            if f.is_file() and f.suffix == ".txt":
                version = self._parse_version(f.name)
                prompts.append({
                    "filename": f.name,
                    "version": ".".join(map(str, version)),
                    "size": f.stat().st_size
                })
        
        return sorted(prompts, key=lambda x: tuple(map(int, x["version"].split("."))), reverse=True)

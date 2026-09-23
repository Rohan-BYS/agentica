import re
from typing import Dict

class SecretManager:
    """
    Prevents sensitive data from leaking into LLM context.
    """
    def __init__(self):
        self.secrets: Dict[str, str] = {}
        self.secret_counter = 0
        
        self.patterns = [
            re.compile(r'(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})'), # GitHub PATs
            re.compile(r'sk-[a-zA-Z0-9]{48}'), # OpenAI keys
            re.compile(r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'), # JWTs
            re.compile(r'Bearer\s+[a-zA-Z0-9_\-\.]+'), # Bearer tokens
            re.compile(r'AKIA[0-9A-Z]{16}'), # AWS Access Keys
        ]

    def redact(self, text: str) -> str:
        """Replace sensitive strings with opaque handles."""
        if not text:
            return text
            
        redacted_text = text
        for pattern in self.patterns:
            matches = pattern.findall(redacted_text)
            for match in matches:
                # To handle Bearer token full match replacing
                if isinstance(match, tuple):
                    match = match[0]
                self.secret_counter += 1
                handle = f"${{nexus_secret_{self.secret_counter}}}"
                self.secrets[handle] = match
                redacted_text = redacted_text.replace(match, handle)
                
        return redacted_text

    def resolve(self, text: str) -> str:
        """Replace handles back to real values."""
        if not text:
            return text
            
        resolved_text = text
        for handle, secret in self.secrets.items():
            resolved_text = resolved_text.replace(handle, secret)
            
        return resolved_text

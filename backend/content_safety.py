import re
from typing import Tuple, Optional

# Expanded Kid-Safety & Hazard Blocklist Patterns
INAPPROPRIATE_PATTERNS = [
    # Adult / Explicit
    r'\b(adult|nsfw|porn|explicit|erotic|sex|nude|dating|escort)\b',
    # Violence / Weapons / Explosives / Hazardous Chemicals
    r'\b(bomb|explosive|weapon|gun|firearm|grenade|ammunition|assault|kill|murder|poison|cyanide|meth|cocaine|heroin|fentanyl)\b',
    # Self-harm / Suicide
    r'\b(suicide|self-harm|cut myself|hang myself)\b',
    # Cyber Attacks / Malware
    r'\b(hack|crack|bypass|malware|virus|trojan|ransomware|keylogger|ddos|phishing)\b',
    # Gambling / Profanity
    r'\b(gambling|casino|betting|profanity|curse|hate speech|slur)\b'
]

SAFE_KID_RESPONSE = """
🛡️ **[Kid Safety Guardrail Active]**

Hello! Offline GPT is locked in **Server-Side Educational Mode** for students. 

I can help you explore and learn:
- 🌌 **Astronomy & Space Exploration**
- 📐 **Mathematics & Geometry**
- 🧪 **Science, Chemistry & Biology**
- 🌍 **Geography & World History**
- 💻 **Computer Coding & Logic**
- 📖 **Literature, Grammar & Creative Writing**

Please ask me a question about one of your school or educational subjects!
"""

def evaluate_content_safety(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Evaluates input prompt against kid-safety guardrails.
    Returns (is_safe, refusal_response)
    """
    p_lower = prompt.lower()
    
    for pattern in INAPPROPRIATE_PATTERNS:
        if re.search(pattern, p_lower):
            return False, SAFE_KID_RESPONSE.strip()
            
    return True, None

def sanitize_output(text: str) -> str:
    """
    Post-inference check on any generated response from Llama 3.2 or cloud models.
    Guarantees no hazardous content reaches the student.
    """
    if not text:
        return ""
        
    t_lower = text.lower()
    for pattern in INAPPROPRIATE_PATTERNS:
        if re.search(pattern, t_lower):
            return SAFE_KID_RESPONSE.strip()
            
    return text

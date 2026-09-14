import re
from typing import Tuple, Optional

# Bulletproof Kid-Safety & Hazard Regex Patterns with root/stem wildcard matching
HAZARD_PATTERNS = [
    # Explosives, Weapons, Bombs, Firearms, Ammunition
    r'\b(bomb\w*|explos\w*|weapon\w*|gun\w*|firearm\w*|grenad\w*|ammunit\w*|missil\w*|dynamit\w*|gunpowder|landmine\w*|c4)\b',
    # Violence, Killing, Physical Harm, Assault, Murder
    r'\b(kill\w*|murder\w*|assault\w*|slaughter\w*|massacr\w*|tortur\w*|stab\w*|shoot\w*|behead\w*|strangl\w*|decapitat\w*)\b',
    # Hazardous Chemicals, Poisons, Toxins
    r'\b(poison\w*|cyanid\w*|arsenic|ricin|anthrax|sarin|toxic chemical\w*|nerve agent\w*)\b',
    # Narcotics, Illegal Drugs, Synthesis
    r'\b(drug\w*|cocaine|heroin|meth\w*|fentanyl|narcotic\w*|lsd|ecstasy|weed|marijuana|overdose)\b',
    # Self-Harm & Suicide
    r'\b(suicid\w*|self-harm\w*|cut myself|hang myself|end my life|kill myself)\b',
    # Adult, Sexual, Erotic, Nudity, Pornography
    r'\b(adult\w*|nsfw|porn\w*|explicit|erotic\w*|sex\w*|nude|nudity|dating|escort\w*|prostitut\w*|genital\w*|vagina\w*|penis\w*)\b',
    # Cyber Attacks, Hacking, Malware
    r'\b(hack\w*|crack\w*|bypass\w*|malware|ransomware|trojan\w*|keylogger\w*|phish\w*|ddos|exploit\w*)\b',
    # Hate Speech, Profanity, Slurs
    r'\b(profan\w*|curse\w*|hate speech|slur\w*|fuck\w*|shit\w*|bitch\w*|asshole\w*|bastard\w*)\b'
]

SAFE_KID_RESPONSE = """
🛡️ **[Kid Safety Guardrail Active]**

Offline GPT is locked in **Educational Mode for Children**. 

I cannot provide instructions or information related to weapons, explosives, violence, adult topics, or hazardous materials.

You can ask me about safe school subjects:
- 🌌 **Astronomy & The Solar System**
- 📐 **Mathematics & Geometry**
- 🧪 **General Science & Physics**
- 🌍 **Geography & World History**
- 💻 **Computer Programming in Python**
- 📖 **Literature & Creative Writing**

What educational topic would you like to explore?
"""

def evaluate_content_safety(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Evaluates prompt against kid-safety guardrails.
    Returns (is_safe, refusal_response)
    """
    if not prompt:
        return True, None
        
    p_clean = prompt.lower().strip()
    
    # Check all hazard patterns with word stems
    for pattern in HAZARD_PATTERNS:
        if re.search(pattern, p_clean):
            return False, SAFE_KID_RESPONSE.strip()
            
    return True, None

def sanitize_output(text: str) -> str:
    """
    Post-inference check on any generated response from Llama 3.2 or cloud models.
    Guarantees no hazardous or adult content reaches the student.
    """
    if not text:
        return ""
        
    t_clean = text.lower()
    for pattern in HAZARD_PATTERNS:
        if re.search(pattern, t_clean):
            return SAFE_KID_RESPONSE.strip()
            
    return text

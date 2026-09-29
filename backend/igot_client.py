import random
from typing import List, Dict

# Mock Database of iGOT Karmayogi Courses
MOCK_IGOT_CATALOG = [
    {"id": "igot_101", "title": "Introduction to Big Data Analytics in Governance", "provider": "Ministry of Statistics", "duration": "4 Hours", "tags": ["big data", "analytics", "statistics"]},
    {"id": "igot_102", "title": "Advanced R Programming for Data Science", "provider": "National Informatics Centre", "duration": "10 Hours", "tags": ["r", "programming", "data science"]},
    {"id": "igot_103", "title": "Machine Learning for Public Policy", "provider": "NITI Aayog", "duration": "6 Hours", "tags": ["machine learning", "ai", "public policy", "python"]},
    {"id": "igot_104", "title": "Survey Design and Digital Data Collection", "provider": "Ministry of Statistics", "duration": "3 Hours", "tags": ["survey", "data collection", "field work"]},
    {"id": "igot_105", "title": "Data Visualization for Government Officials", "provider": "Capacity Building Commission", "duration": "5 Hours", "tags": ["visualization", "dashboard", "tableau", "powerbi"]},
    {"id": "igot_106", "title": "Cybersecurity Basics for Data Officers", "provider": "CERT-In", "duration": "2 Hours", "tags": ["security", "cybersecurity", "privacy"]}
]

def search_igot_courses(skill_gap: str) -> List[Dict]:
    """
    Simulates searching the iGOT Karmayogi Course Catalog via REST API.
    In a production environment, this would use requests.post to the actual iGOT Sunbird API.
    """
    skill_lower = skill_gap.lower()
    results = []
    
    # Simple keyword matching against tags and title
    for course in MOCK_IGOT_CATALOG:
        if any(skill_lower in tag.lower() for tag in course["tags"]) or skill_lower in course["title"].lower():
            results.append(course)
            
    # If no specific match, return a random generic recommendation to simulate fuzzy search
    if not results:
        results = random.sample(MOCK_IGOT_CATALOG, 2)
        
    return results

def sync_user_certificates(user_id: str) -> List[str]:
    """
    Simulates fetching a user's completed certificates from iGOT telemetry.
    """
    # Mocking that the user has completed one or two courses
    return ["Data Visualization for Government Officials", "Survey Design and Digital Data Collection"]

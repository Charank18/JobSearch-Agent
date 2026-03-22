"""
Prompt templates for AI agents.
"""

RESUME_DATA = {
    "name": "Charan Karnati",
    "github": "Charank18",
    "linkedin": "charankarnati",
    "email": "charankarnati180604@gmail.com",
    "education": {
        "institution": "National Institute of Technology (NIT), Andhra Pradesh",
        "degree": "B.Tech - Computer Science & Engineering, summa cum laude",
        "cgpa": "9.07",
    },
    "experience": [
        {
            "company": "Myntra (Flipkart)",
            "role": "Software Developer Intern - Supply Chain Management",
            "period": "Jan 2026 - Present",
            "highlights": [
                "Built Probability Sell-Through Model improving forecast accuracy by 18%",
                "Designed time-series forecasting pipelines (LightGBM, XGBoost) reducing OOS incidents by 10%",
                "Engineered MIP-based replenishment engine using Google OR-Tools (SCIP solver)",
                "Optimized allocation algorithms improving GMV per cluster by 8%",
                "Owned end-to-end supply chain ML pipeline processing 100K+ daily order signals",
            ],
        },
        {
            "company": "Annam.AI",
            "role": "Software Engineer Intern",
            "period": "May 2025 - Dec 2025",
            "highlights": [
                "Architected full-stack generative AI pipeline (Express, TypeScript, InversifyJS) serving 100+ beta users",
                "Automated course-item creation reducing manual curation time by 65%",
                "Integrated JWT-based auth and role-based access control",
            ],
        },
        {
            "company": "AIISC, University of South Carolina",
            "role": "Student Researcher (Remote)",
            "period": "Feb 2025 - May 2025",
            "highlights": [
                "Engineered multi-agent simulation with LLM-driven agents in geospatially accurate NYC environment",
                "Built interactive real-time visualization dashboard using Mapbox GL JS",
            ],
        },
    ],
    "publications": [
        "Meta-Heuristic Algorithms for Quasi Total Double Roman Domination Problem (RAIRO: ITA, H-index 39)",
        "Quantum Key Distribution Protocols (16th IEEE ICCCNT)",
        "Quantum Approaches to NP-Hard Combinatorial Optimization Problems (MCCS-2025)",
    ],
    "skills": {
        "languages": ["Python", "C++", "Java", "JavaScript", "TypeScript", "SQL"],
        "frameworks": ["React", "Node.js", "Express", "Django", "FastAPI", "LangChain", "Google OR-Tools"],
        "ml_ai": ["PyTorch", "TensorFlow", "scikit-learn", "LightGBM", "HuggingFace Transformers", "SpaCy", "NLTK", "Pandas", "NumPy"],
        "infra": ["Git", "Docker", "Linux", "REST APIs", "CI/CD", "AWS/GCP"],
    },
}


CV_GENERATION_PROMPT = """You are an expert CV/resume writer. Generate a tailored CV for the following job posting.

CANDIDATE PROFILE:
Name: {name}
Education: {education}
Experience: {experience}
Skills: {skills}
Publications: {publications}

JOB DETAILS:
Title: {job_title}
Company: {job_company}
Location: {job_location}
Description: {job_description}

INSTRUCTIONS:
1. Tailor the CV to highlight relevant experience and skills for this specific role
2. Use professional language and quantified achievements
3. Keep it concise (max 2 pages worth of content)
4. Emphasize matching technical skills and domain experience
5. Do NOT invent or fabricate any experience or skills not present in the profile
6. Present the candidate as a strong professional - do not reference graduation year or academic status
7. Format with clear sections: Summary, Experience, Education, Skills, Publications

Generate the tailored CV now:"""


COVER_LETTER_PROMPT = """You are an expert career coach. Write a compelling, personalized cover letter.

CANDIDATE PROFILE:
Name: {name}
Current Role: {current_role}
Key Skills: {skills}
Notable Achievement: {achievement}

JOB DETAILS:
Title: {job_title}
Company: {job_company}
Description: {job_description}

INSTRUCTIONS:
1. Open with genuine enthusiasm for the specific role and company
2. Connect 2-3 relevant experiences directly to job requirements
3. Show understanding of the company's mission/product
4. Close with a confident call to action
5. Keep it under 400 words
6. Professional but personable tone
7. Do NOT mention graduation timeline or student status

Write the cover letter now:"""


JOB_PARSER_PROMPT = """Extract structured information from this job posting.

JOB POSTING:
{job_text}

Extract and return a JSON object with these fields:
- title: Job title
- company: Company name
- location: Job location(s)
- employment_type: Full-time/Part-time/Contract/Internship
- experience_required: Years of experience or level
- salary_range: If mentioned
- skills_required: List of required technical skills
- skills_preferred: List of nice-to-have skills
- responsibilities: List of key responsibilities
- qualifications: List of required qualifications
- benefits: List of benefits if mentioned
- application_deadline: If mentioned
- remote_policy: Remote/Hybrid/On-site

Return ONLY valid JSON."""

"""OG Group taxonomy. Pure data so it can be maintained without touching logic.

Keyword weights: 4 = near-definitive signal, 3 = strong, 2 = supportive, 1 = weak context.
Descriptions feed the similarity scorer (TF-IDF or embeddings).
"""

OG_GROUPS: dict[str, dict] = {
    "State & Local": {
        "description": "City, county and state government consulting: strategic planning, "
        "organizational assessment, operating model, process improvement, service delivery "
        "and operational efficiency reviews.",
        "keywords": {
            "strategic plan": 3, "operational efficiency": 3, "operating model": 3,
            "organizational assessment": 3, "process improvement": 3, "service delivery": 2,
            "county": 2, "municipal": 2, "city council": 2, "special district": 2,
            "performance audit": 3, "public sector": 1,
        },
    },
    "K-12": {
        "description": "School district consulting: enrollment projections, attendance "
        "boundaries, redistricting, student assignment and school planning.",
        "keywords": {
            "school district": 3, "enrollment": 3, "attendance boundary": 4, "redistricting": 4,
            "student assignment": 3, "school planning": 3, "k-12": 4, "superintendent": 2,
            "students": 1, "schools": 1, "demographic stud": 2,
        },
    },
    "HIED": {
        "description": "Higher education advisory for universities and colleges: ERP, SIS, "
        "enterprise systems, academic and administrative modernization.",
        "keywords": {
            "higher education": 4, "university": 3, "college": 2, "sis": 3,
            "student information system": 4, "erp": 2, "campus": 2, "provost": 3,
            "enterprise systems": 2,
        },
    },
    "HC Solutions": {
        "description": "Human capital consulting: classification and compensation studies, "
        "pay equity, salary benchmarking, job descriptions, HR and organizational analysis.",
        "keywords": {
            "compensation": 3, "classification and compensation": 4, "pay equity": 4,
            "salary": 2, "job description": 3, "reclassification": 3, "human resources": 2,
            "hr consulting": 3, "benchmarking": 1, "total rewards": 3,
        },
    },
    "HC Staffing": {
        "description": "Staff augmentation and interim leadership: temporary personnel, "
        "interim executives, contract staffing placements.",
        "keywords": {
            "staff augmentation": 4, "interim": 3, "temporary personnel": 4,
            "temporary technology staffing": 4, "staffing": 3, "personnel": 1, "placement": 2,
        },
    },
    "Economic Mobility": {
        "description": "Workforce development, labor market analysis, disparity studies, "
        "supplier diversity, economic inclusion and economic impact.",
        "keywords": {
            "workforce development": 3, "labor market": 3, "disparity": 4,
            "supplier diversity": 3, "economic inclusion": 3, "economic mobility": 4,
            "dbe": 2, "mbe": 2, "economic impact": 2, "workforce board": 3,
        },
    },
    "Facilities Planning": {
        "description": "Facility condition assessments, capital improvement planning, "
        "deferred maintenance prioritization, space capacity and utilization analysis.",
        "keywords": {
            "facility condition": 4, "capital planning": 3, "capital improvement": 3,
            "deferred maintenance": 3, "utilization": 2, "educational adequacy": 3,
            "facilities master plan": 4, "building condition": 3, "space planning": 3,
        },
    },
    "Social Impact": {
        "description": "Nonprofit and human services advisory: program evaluation, "
        "homelessness systems, supportive housing, behavioral health and equity outcomes.",
        "keywords": {
            "homelessness": 4, "supportive housing": 3, "coordinated entry": 4,
            "program evaluation": 3, "nonprofit": 2, "hmis": 3, "human services": 3,
            "behavioral health": 2, "participant outcome": 2,
        },
    },
}

# Non-target trades work. Matches preceded by a negation ("not seeking ... construction") are ignored.
REJECT_TERMS: dict[str, int] = {
    "hvac": 3, "plumbing": 3, "janitorial": 4, "custodial": 3, "landscaping": 4,
    "lawn": 2, "paving": 4, "asphalt": 3, "pest control": 4, "roofing": 4,
    "construction": 2, "demolition": 3, "ductwork": 3, "licensed contractor": 3,
    "labor, materials": 3, "invitation for bids": 2, "general contractor": 3,
    "installation": 1, "mechanical contracting": 4,
}

# Evidence the buyer wants advisory work; protects consulting leads that mention trades words.
CONSULTING_CUES: dict[str, int] = {
    "consult": 2, "assessment": 1, "study": 1, "evaluation": 1, "advisor": 2,
    "advisory": 2, "recommendation": 1, "roadmap": 1, "analysis": 1, "planning": 1,
}

# Explicit statements that no consulting is wanted.
ANTI_CONSULTING = ["no consulting services", "consulting services are not"]

# Business policy: these groups always go to a human.
REVIEW_GROUPS = {"HC Staffing"}

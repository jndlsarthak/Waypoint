"""Registry of source pages to ingest for Phase 1.

Each entry is an official canada.ca / IRCC guidance page. URLs were confirmed
against live search results (not guessed) and checked against
https://www.canada.ca/robots.txt, which does not disallow any of these paths.
"""

PAGES = [
    {
        "slug": "study-permit-eligibility",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/eligibility.html",
        "topic_tags": ["study-permit", "eligibility"],
    },
    {
        "slug": "study-permit-overview",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit.html",
        "topic_tags": ["study-permit", "overview"],
    },
    {
        "slug": "study-permit-apply",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/apply.html",
        "topic_tags": ["study-permit", "how-to-apply"],
    },
    {
        "slug": "pgwp-eligibility",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html",
        "topic_tags": ["pgwp", "eligibility"],
    },
    {
        "slug": "pgwp-about",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/about.html",
        "topic_tags": ["pgwp", "overview"],
    },
    {
        "slug": "pgwp-field-of-study",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility/field-of-study.html",
        "topic_tags": ["pgwp", "field-of-study"],
    },
    {
        "slug": "work-off-campus",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/work-off-campus.html",
        "topic_tags": ["off-campus-work"],
    },
    {
        "slug": "work-on-campus",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/work-on-campus.html",
        "topic_tags": ["on-campus-work"],
    },
    {
        "slug": "study-canada-overview",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada.html",
        "topic_tags": ["study-canada", "overview"],
    },
    {
        "slug": "work-while-studying-overview",
        "url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work.html",
        "topic_tags": ["working-while-studying", "overview"],
    },
]

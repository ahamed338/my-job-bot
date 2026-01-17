import os
import sys
from jobspy import scrape_jobs
from google import genai
import pandas as pd

# --- SECURITY: Load Key from GitHub Secrets ---
# This ensures your key is NEVER hardcoded in the file
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ Error: GEMINI_API_KEY not found. Add it to GitHub Secrets!")
    sys.exit(1)

# --- CONFIGURATION ---
SEARCH_TERM = "Engineering Manager Platform"
LOCATION = "Bangalore, India"
RESULTS_WANTED = 15     # Number of jobs to fetch per site
HOURS_OLD = 24          # Only fetch jobs posted in the last 24 hours
TARGET_SITES = ["linkedin", "indeed", "glassdoor", "google"]

# --- YOUR PROFILE ---
MY_RESUME = """
Senior Platform Engineering Manager | 16+ Years Exp
Skills: Azure, AKS, FinOps ($200k savings), Python, Team Management (7+ engineers).
"""

def get_gemini_score(job_description):
    """Asks Gemini to score the job 0-100"""
    try:
        client = genai.Client(api_key=API_KEY)
        prompt = f"""
        Compare this Job Description (JD) to my Resume.
        RESUME: {MY_RESUME}
        JD: {job_description[:2500]}
        
        OUTPUT ONLY ONE NUMBER: The match percentage (0-100).
        """
        response = client.models.generate_content(
            model="gemini-flash-latest", 
            contents=prompt
        )
        # Clean up response to get just the number
        return int(response.text.strip().replace('%', ''))
    except Exception as e:
        print(f"   (AI Error: {e})", end="")
        return 0

def start_hunting():
    print(f"🕵️‍♂️ Hunting for '{SEARCH_TERM}' across {TARGET_SITES}...")
    
    try:
        jobs = scrape_jobs(
            site_name=TARGET_SITES,
            search_term=SEARCH_TERM,
            location=LOCATION,
            results_wanted=RESULTS_WANTED,
            hours_old=HOURS_OLD,
            country_indeed='India'
        )
    except Exception as e:
        print(f"⚠️ Scraper Error: {e}")
        return

    print(f"✅ Found {len(jobs)} raw jobs. Filtering with AI...")
    
    match_count = 0
    
    for index, job in jobs.iterrows():
        title = job.get('title', 'Unknown')
        company = job.get('company', 'Unknown')
        apply_url = job.get('job_url', '#')
        description = job.get('description', '')

        if not description or len(str(description)) < 100:
            continue

        print(f"   Checking: {title[:30]}...", end="")
        score = get_gemini_score(description)
        print(f" Score: {score}%")
        
        if score >= 80:
            match_count += 1
            print(f"\n🎯 MATCH FOUND: {score}%")
            print(f"   Role: {title}")
            print(f"   Firm: {company}")
            print(f"   Link: {apply_url}")
            print("-" * 40)

    if match_count == 0:
        print("\nNo high-value matches found today.")
    else:
        print(f"\n✨ Job Hunt Complete. Found {match_count} top-tier jobs.")

if __name__ == "__main__":
    start_hunting()

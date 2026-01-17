import os
import sys
import json
import urllib.request
import urllib.parse
import time
from jobspy import scrape_jobs
import pandas as pd
from dotenv import load_dotenv # Import the library

# --- FIX 1: LOAD LOCAL ENV VARIABLES ---
# This reads your .env file when running locally. 
# On GitHub, it does nothing (which is fine).
load_dotenv() 

# DO NOT put the actual keys here. 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN:
    # This error helps you know if your secrets aren't loading
    raise ValueError("Missing API Keys! Check your .env file (local) or GitHub Secrets.")

# --- 2. TELEGRAM NOTIFICATION ---
def send_telegram_message(message):
    """Send message to Telegram"""
    # ... (Keep your existing Telegram code here) ...
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req) as response:
            return True
    except Exception as e:
        print(f"   (Telegram Error: {e})")
        return False

# --- 3. SMART KEYWORD FILTER ---
def keyword_prefilter(title, description):
    # ... (Keep your existing filter code here) ...
    # Ensure inputs are strings to prevent errors
    title_lower = str(title).lower() if title else ""
    desc_lower = str(description).lower() if description else ""
    
    # HARD EXCLUDE
    exclude_in_title = [
        'quality assurance', 'qa engineer', 'test engineer', 'sdet',
        'data analyst', 'business analyst', 'sales', 'support engineer',
        'junior', 'intern', 'entry level',
        'network engineer', 'help desk', 'service desk',
        'director', 'vp', 'vice president', 'head of', 'chief',
        'distinguished', 'chemist', 'scientist', 'researcher', 'medical', 'pharma'
    ]
    
    for exclude in exclude_in_title:
        if exclude in title_lower:
            return False, "Wrong level/role"
    
    # YOUR TARGET ROLES
    perfect_titles = [
        'engineering manager', 'platform manager', 'devops manager',
        'sre manager', 'infrastructure manager', 'technical manager',
        'engineering lead', 'technical lead', 'team lead', 'devops lead',
        'manager, platform', 'manager, devops', 'manager, infrastructure',
        'associate manager', 'delivery manager', 
        'software engineering manager', 'software manager',
        'manager sw', 'sw engineering', 'manager 3', 'manager ii', 'manager iii'
    ]
    
    for keyword in perfect_titles:
        if keyword in title_lower:
            return True, "Perfect title match"
    
    if len(desc_lower) < 100:
        return False, "Need description to evaluate"
    
    # SKILLS
    your_skills = [
        'kubernetes', 'k8s', 'aks', 'eks', 'azure', 'aws', 'cloud',
        'platform engineering', 'platform', 'internal developer platform', 'idp',
        'terraform', 'infrastructure as code', 'iac',
        'finops', 'cost optimization', 'gitops', 'ci/cd', 'devops', 'sre',
        'docker', 'container', 'team lead', 'engineering management', 'manage team'
    ]
    
    skill_matches = sum(1 for skill in your_skills if skill in desc_lower)
    
    if skill_matches >= 2:
        return True, f"Skill match ({skill_matches} skills)"
    
    if ('manager' in title_lower or 'lead' in title_lower) and skill_matches >= 1:
        return True, "Leadership + tech skills"
    
    return False, "Not relevant"

# --- 4. AI FUNCTION ---
def ask_gemini_stealth(prompt):
    # ... (Keep your existing AI code here) ...
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"   (AI Error: {e})", end="")
        return "0"

# --- 5. CONFIGURATION ---
SEARCH_STRATEGIES = ["Engineering Manager DevOps", "Platform Engineering Manager", "Technical Lead Platform"]
LOCATIONS = ["Bangalore", "Hyderabad", "Chennai"]
RESULTS_PER_SEARCH = 10
HOURS_OLD = 72
TARGET_SITES = ["indeed", "linkedin"]

MY_RESUME = """
Platform Engineering Manager | 16+ Years Experience | First American India
Current: Associate Manager - Platform Engineering & DevOps
Skills: Azure, AWS, Kubernetes, Terraform, Team Management (7 engineers)
"""

def start_hunting():
    print(f"🔌 Testing Connections...")
    
    # Test Gemini
    print(f"   - Gemini AI...", end="")
    test = ask_gemini_stealth("Reply 'OK'")
    if "OK" not in test:
        print(f" ❌ Failed")
        # Don't return, try to continue
    else:
        print(" ✅")
    
    # Test Telegram (Simplified check)
    print(f"   - Telegram...", end="")
    if send_telegram_message("🤖 Job Hunter Started!"):
        print(" ✅")
    else:
        print(" ⚠️ (Optional)")
    
    all_jobs = []
    for location in LOCATIONS:
        for search_term in SEARCH_STRATEGIES:
            print(f"\n🕵️‍♂️ Scraping: '{search_term}' in {location}...")
            try:
                # Add random delay to avoid bot detection
                time.sleep(2) 
                jobs = scrape_jobs(
                    site_name=TARGET_SITES,
                    search_term=search_term,
                    location=f"{location}, India",
                    results_wanted=RESULTS_PER_SEARCH,
                    hours_old=HOURS_OLD,
                    country_indeed='India'
                )
                print(f"   Found {len(jobs)} jobs")
                all_jobs.append(jobs)
            except Exception as e:
                print(f"   ⚠️ Error: {e}")
                continue
    
    if not all_jobs:
        print("\n❌ No jobs found.")
        return
    
    jobs = pd.concat(all_jobs, ignore_index=True)
    jobs = jobs.drop_duplicates(subset=['job_url'], keep='first')
    print(f"\n✅ Total unique jobs found: {len(jobs)}")
    
    # Phase 1: Filtering
    promising_jobs = []
    for index, job in jobs.iterrows():
        title = job.get('title', 'Unknown')
        description = job.get('description', '') # Might be None or empty
        
        is_match, reason = keyword_prefilter(title, description)
        
        if is_match:
            promising_jobs.append(job)
            print(f"   ✅ {str(title)[:50]} - {reason}")

    if not promising_jobs:
        print("\n❌ No promising jobs found.")
        return
    
    # Phase 2: AI Analysis
    print(f"\n🤖 PHASE 2: AI Analysis on {len(promising_jobs)} promising jobs...")
    
    for i, job in enumerate(promising_jobs):
        if i >= 10: break # Limit calls
        
        title = job.get('title', 'Unknown')
        location = job.get('location', 'Unknown')
        apply_url = job.get('job_url', '#')
        
        # --- FIX 2: PREVENT CRASH IF DESCRIPTION IS NONE ---
        description = job.get('description')
        if not description:
            description = "No description available."
        
        # Safe slicing
        desc_truncated = description[:1500] 
        
        print(f"\n   Analyzing: {str(title)[:35]}...", end="")
        
        prompt = f"""
        Score match (0-100).
        RESUME: {MY_RESUME}
        JOB: {title} in {location}
        DESC: {desc_truncated}
        Output ONLY number.
        """
        
        score_text = ask_gemini_stealth(prompt)
        time.sleep(4)
        
        try:
            score = int(''.join(filter(str.isdigit, score_text)))
        except:
            score = 0
        
        print(f" {score}%")
        
        if score >= 55:
            message = f"🎯 <b>MATCH: {score}%</b>\n\n<b>{title}</b>\n📍 {location}\n\n<a href='{apply_url}'>👉 APPLY NOW</a>"
            send_telegram_message(message)

if __name__ == "__main__":
    start_hunting()
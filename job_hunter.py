import os
import sys
import json
import urllib.request
import urllib.parse
import time
from jobspy import scrape_jobs
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- 1. YOUR KEYS ---
GEMINI_API_KEY = "AIzaSyAl7tBq14f5BRepK8Ogca85K17AhZWX4g0".strip()
TELEGRAM_BOT_TOKEN = "8559611699:AAEUTJsOrfocPonseVRObrpZ20H2svVQotw".strip()
TELEGRAM_CHAT_ID = "6597911351".strip()

# --- 2. TELEGRAM NOTIFICATION ---
def send_telegram_message(message):
    """Send message to Telegram"""
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

# --- 3. SMART KEYWORD FILTER (FREE - NO API CALLS) ---
def keyword_prefilter(title, description):
    """Quick keyword check before using expensive AI"""
    title_lower = str(title).lower()
    desc_lower = str(description).lower()
    
    # HARD EXCLUDE - Skip these in title
    exclude_in_title = [
        'quality assurance', 'qa engineer', 'test engineer', 'sdet',
        'data analyst', 'business analyst', 'sales', 'support engineer',
        'junior', 'intern', 'entry level',
        'network engineer', 'help desk', 'service desk',
        'director', 'vp', 'vice president', 'head of', 'chief',
        'distinguished',
        'chemist', 'scientist', 'researcher', 'medical', 'pharma'
    ]
    
    for exclude in exclude_in_title:
        if exclude in title_lower:
            return False, "Wrong level/role"
    
    # YOUR TARGET ROLES - Manager who does both people + technical
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
    
    # For jobs without perfect titles, need good description
    if len(desc_lower) < 100:
        return False, "Need description to evaluate"
    
    # YOUR CORE SKILLS
    your_skills = [
        'kubernetes', 'k8s', 'aks', 'eks',
        'azure', 'aws', 'cloud',
        'platform engineering', 'platform', 'internal developer platform', 'idp',
        'terraform', 'infrastructure as code', 'iac',
        'finops', 'cost optimization',
        'gitops', 'ci/cd', 'devops', 'sre',
        'docker', 'container',
        'team lead', 'engineering management', 'manage team', 'people management'
    ]
    
    skill_matches = sum(1 for skill in your_skills if skill in desc_lower)
    
    if skill_matches >= 2:
        return True, f"Skill match ({skill_matches} skills)"
    
    if ('manager' in title_lower or 'lead' in title_lower) and skill_matches >= 1:
        return True, "Leadership + tech skills"
    
    return False, "Not relevant"

# --- 4. AI FUNCTION ---
def ask_gemini_stealth(prompt):
    """Uses Gemini AI to score job matches"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    data = json.dumps({
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            return result['candidates'][0]['content']['parts'][0]['text']
    except urllib.error.HTTPError as e:
        print(f"   (AI Error {e.code})", end="")
        return "0"
    except Exception as e:
        print(f"   (Error: {e})", end="")
        return "0"

# --- 5. CONFIGURATION ---
SEARCH_STRATEGIES = [
    "Engineering Manager DevOps",
    "Platform Engineering Manager", 
    "Technical Lead Platform",
    "DevOps Team Lead"
]
LOCATIONS = ["Bangalore", "Hyderabad", "Chennai"]
RESULTS_PER_SEARCH = 10
HOURS_OLD = 72
TARGET_SITES = ["indeed", "linkedin"]

MY_RESUME = """
Platform Engineering Manager | 16+ Years Experience | First American India

CURRENT ROLE (Apr 2025 - Present):
- Associate Manager - Platform Engineering & DevOps (Engineering Manager)
- Managing team of 7 DevOps Engineers (people management + technical oversight)
- Handle hiring, performance reviews, career coaching, team scaling

LEADERSHIP STRENGTHS:
- People Management: Team of 7, hiring, performance appraisals, mentoring
- Technical Oversight: Guide architecture, review designs, not hands-on coding
- Delivery Management: Sprint planning, stakeholder management, Agile/Scrum
- Platform Strategy: Define roadmaps, prioritize initiatives, align with business

TECHNICAL BACKGROUND (Oversight, not hands-on):
- Cloud Platforms: Azure (AKS), AWS, Multi-cloud
- Platform Tools: Kubernetes, Terraform, CI/CD, GitOps
- Cost Management: FinOps, cloud optimization ($200k+ savings)
- AI Integration: GenAI tools for team productivity

IDEAL ROLE:
Engineering Manager, Platform Manager, DevOps Manager, Technical Lead, Delivery Manager
- Mix of people management (60%) + technical guidance (40%)
- Team size: 5-10 engineers
- NOT looking for: Director/VP roles, Pure IC/Architect roles, Hands-on coding positions
"""

def start_hunting():
    print(f"🔌 Testing Connections...")
    
    # Test Gemini
    print(f"   - Gemini AI...", end="")
    test = ask_gemini_stealth("Reply 'OK'")
    if "OK" not in test:
        print(f" ❌ Failed")
        return
    print(" ✅")
    
    # Test Telegram
    if TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print(f"   - Telegram...", end="")
        if send_telegram_message("🤖 Job Hunter Started! Searching Bangalore, Hyderabad, Chennai..."):
            print(" ✅")
        else:
            print(" ⚠️ (Optional - continuing anyway)")
    
    # Try multiple search strategies and locations
    all_jobs = []
    for location in LOCATIONS:
        for search_term in SEARCH_STRATEGIES:
            print(f"\n🕵️‍♂️ Scraping: '{search_term}' in {location}...")
            try:
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
                time.sleep(2)
            except Exception as e:
                print(f"   ⚠️ Error: {e}")
                continue
    
    if not all_jobs:
        print("\n❌ No jobs found from any search")
        return
    
    # Combine and deduplicate
    jobs = pd.concat(all_jobs, ignore_index=True)
    jobs = jobs.drop_duplicates(subset=['job_url'], keep='first')
    
    print(f"\n✅ Total unique jobs found: {len(jobs)}")
    
    # Debug sample
    print(f"\n🔍 Sample of jobs found:")
    for i in range(min(10, len(jobs))):
        print(f"   {i+1}. {jobs.iloc[i].get('title', 'No title')}")
    
    print(f"\n📊 PHASE 1: Keyword Pre-filtering (FREE)...")
    
    # Phase 1: Fast keyword filtering
    promising_jobs = []
    for index, job in jobs.iterrows():
        title = job.get('title', 'Unknown')
        description = job.get('description', '')
        
        is_match, reason = keyword_prefilter(title, description)
        
        if is_match:
            promising_jobs.append(job)
            print(f"   ✅ {title[:50]} - {reason}")
        elif len(str(description)) >= 100:
            if index < 10:
                print(f"   ⏭️  {title[:50]} ({reason})")
    
    if len(promising_jobs) == 0:
        print("\n❌ No promising jobs found after keyword filtering")
        print("💡 Try broader search terms or check back later")
        return
    
    print(f"\n🤖 PHASE 2: AI Analysis on {len(promising_jobs)} promising jobs...")
    
    matches_found = []
    api_calls = 0
    max_api_calls = 10
    
    for job in promising_jobs:
        if api_calls >= max_api_calls:
            print(f"\n⚠️ Reached API limit ({max_api_calls} calls). Stopping to avoid rate limits.")
            break
        
        title = job.get('title', 'Unknown')
        company = job.get('company', 'Unknown')
        location = job.get('location', 'Unknown')
        apply_url = job.get('job_url', '#')
        description = job.get('description', '')
        
        print(f"\n   Analyzing: {title[:35]}...", end="")
        
        prompt = f"""
Score this job match (0-100) based on my resume.

MY RESUME:
{MY_RESUME}

JOB:
Title: {title}
Location: {location}
Description: {description[:1500]}

Output ONLY a number 0-100.
        """
        
        score_text = ask_gemini_stealth(prompt)
        api_calls += 1
        time.sleep(4)
        
        try:
            score = int(''.join(filter(str.isdigit, score_text)))
        except:
            score = 0
        
        print(f" {score}%")
        
        if score >= 55:
            matches_found.append({
                'title': title,
                'company': company,
                'location': location,
                'score': score,
                'url': apply_url
            })
            
            print(f"      🎯 HIGH MATCH!")
            
            if TELEGRAM_BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
                message = f"""
🎯 <b>MATCH: {score}%</b>

<b>{title}</b>
{company}
📍 {location}

<a href="{apply_url}">👉 APPLY NOW</a>
                """
                send_telegram_message(message)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 RESULTS:")
    print(f"   - Total jobs scraped: {len(jobs)}")
    print(f"   - Passed keyword filter: {len(promising_jobs)}")
    print(f"   - AI analyzed: {api_calls}")
    print(f"   - High matches (55%+): {len(matches_found)}")
    print(f"{'='*60}")
    
    if len(matches_found) > 0:
        print(f"\n🎯 YOUR MATCHES:\n")
        for match in matches_found:
            print(f"   {match['score']}% - {match['title']}")
            print(f"   {match['company']} | {match['location']}")
            print(f"   {match['url']}\n")
    else:
        print(f"\n💡 No high matches today. Try:")
        print(f"   - Different search terms")
        print(f"   - Run again tomorrow")

if __name__ == "__main__":
    start_hunting()
"""Scrape prerequisite data from university websites for top ranked programs.
Usage: python scrape_prereqs.py [--top N] [--resume]
"""

import csv
import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Set

PREREQ_DB = os.path.join(os.path.dirname(__file__), "prereq_db.json")
PROGRAMS_CSV = os.path.join(os.path.dirname(__file__), 
                            "../../workspace/university_db/programs_v2.csv")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 常见先修课关键词
PREREQ_KEYWORDS = [
    "prerequisite", "prerequisites", "prerequisite courses",
    "program requirements", "admission requirements", "entry requirements",
    "course prerequisites", "academic requirements",
    "prerequisite knowledge", "background requirements",
    "required courses", "required background",
]

# 常见先修课名称
KNOWN_PREREQS = [
    "Calculus I-II", "Calculus I-III", "Linear Algebra",
    "Probability & Statistics", "Statistics", "Discrete Mathematics",
    "Data Structures & Algorithms", "Operating Systems",
    "Database Systems", "Computer Networks", "Programming (Python)",
    "Programming (C++/Java)", "Software Design", "Computer Architecture",
    "Microeconomics", "Macroeconomics", "Financial Accounting",
    "Corporate Finance", "Econometrics", "Financial Mathematics",
    "Thermodynamics", "Material Science", "Fluid Mechanics",
    "Machine Learning", "Artificial Intelligence", "Computer Vision",
    "NLP", "Signals and Systems", "Digital Logic",
    "Electromagnetics", "Quantum Mechanics", "Organic Chemistry",
]

# 手动维护的先修课数据（已验证的高频专业）
MANUAL_PREREQS = {
    "Computer Science": "Data Structures & Algorithms;Programming (Python);Calculus I-II;Linear Algebra;Discrete Mathematics;Probability & Statistics",
    "Data Science": "Calculus I-II;Linear Algebra;Probability & Statistics;Programming (Python);Statistics",
    "Artificial Intelligence": "Calculus I-II;Linear Algebra;Probability & Statistics;Programming (Python);Data Structures & Algorithms;Machine Learning",
    "Software Engineering": "Programming (Python);Programming (C++/Java);Data Structures & Algorithms;Database Systems;Software Design",
    "Electrical Engineering": "Calculus I-III;Linear Algebra;Probability & Statistics;Programming (Python);Signals and Systems;Electromagnetics",
    "Mechanical Engineering": "Calculus I-III;Linear Algebra;Thermodynamics;Material Science;Fluid Mechanics;Programming (Python)",
    "Financial Engineering": "Calculus I-II;Linear Algebra;Probability & Statistics;Programming (Python);Financial Mathematics;Econometrics",
    "Statistics": "Calculus I-II;Linear Algebra;Probability & Statistics;Programming (Python)",
    "Business Analytics": "Statistics;Programming (Python);Calculus I-II;Linear Algebra;Microeconomics",
    "Accounting": "Financial Accounting;Corporate Finance;Microeconomics;Macroeconomics;Statistics",
    "Finance": "Corporate Finance;Financial Accounting;Microeconomics;Macroeconomics;Statistics;Calculus I-II",
    "Economics": "Microeconomics;Macroeconomics;Calculus I-II;Statistics;Econometrics;Linear Algebra",
}

def load_existing() -> Dict:
    if os.path.exists(PREREQ_DB):
        with open(PREREQ_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(db: Dict):
    os.makedirs(os.path.dirname(PREREQ_DB), exist_ok=True)
    with open(PREREQ_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(db)} entries to {PREREQ_DB}")

def find_admissions_url(base_url: str) -> Optional[str]:
    """尝试在网站上找 admissions 页面"""
    try:
        r = requests.get(base_url, timeout=8, headers=HEADERS)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 找 admissions 链接
        for a in soup.find_all('a', href=True):
            text = a.get_text().lower()
            href = a['href']
            if any(kw in text for kw in ["admission", "graduate", "apply", "program"]):
                full = urljoin(base_url, href)
                if urlparse(full).netloc == urlparse(base_url).netloc:
                    return full
        time.sleep(0.5)
        
        # 尝试常见路径
        for path in ["/admissions", "/graduate/admissions", "/apply",
                     "/admission", "/graduate-admissions"]:
            test = base_url.rstrip('/') + path
            tr = requests.get(test, timeout=5, headers=HEADERS)
            if tr.status_code == 200:
                return test
            time.sleep(0.3)
        return None
    except:
        return None

def extract_prereqs_from_page(url: str) -> Optional[List[str]]:
    """从页面提取先修课列表"""
    try:
        r = requests.get(url, timeout=8, headers=HEADERS)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text().lower()
        
        # 检查是否包含先修课关键词
        has_prereq = any(kw in text for kw in PREREQ_KEYWORDS)
        if not has_prereq:
            return None
        
        # 尝试从页面中提取已知先修课
        found = []
        for prereq in KNOWN_PREREQS:
            if prereq.lower() in text:
                found.append(prereq)
        
        return found if found else None
    except:
        return None

def scrape_top(top_n: int = 100, resume: bool = True):
    """爬取 Top N 院校的先修课"""
    db = load_existing() if resume else {}
    
    # 读取 programs
    with open(PROGRAMS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        programs = list(reader)
    
    # 按排名排序并取 top N 所院校
    unis = {}
    for p in programs:
        rank = int(p.get("rank", 999) or 999)
        uni = p["university"].strip()
        if uni not in unis or rank < unis[uni]["rank"]:
            unis[uni] = {"rank": rank, "country": p.get("country", ""),
                        "url": p.get("program_url", ""),
                        "majors": set()}
        unis[uni]["majors"].add(p["major"])
    
    sorted_unis = sorted(unis.items(), key=lambda x: x[1]["rank"])
    target = sorted_unis[:top_n]
    
    print(f"Total unique unis: {len(unis)}")
    print(f"Scraping top {top_n}:")
    
    for i, (name, info) in enumerate(target):
        key = f"{name}|{info['rank']}"
        if key in db:
            print(f"  [{i+1}/{top_n}] SKIP (cached): {name}")
            continue
        
        print(f"  [{i+1}/{top_n}] {name} ({info['country']}) rank={info['rank']}")
        print(f"    URL: {info['url']}")
        
        # 先用 manual 数据
        prereqs_by_major = {}
        for major in info["majors"]:
            if major in MANUAL_PREREQS:
                prereqs_by_major[major] = MANUAL_PREREQS[major]
        
        # 再尝试爬取
        extracted = None
        admissions_url = find_admissions_url(info['url'])
        if admissions_url:
            print(f"    Found admissions: {admissions_url}")
            extracted = extract_prereqs_from_page(admissions_url)
            if extracted:
                prereqs_by_major["_general"] = ";".join(extracted)
                print(f"    Extracted: {extracted}")
        
        if prereqs_by_major:
            db[key] = {
                "name": name,
                "rank": info["rank"],
                "url": info["url"],
                "admissions_url": admissions_url,
                "prereqs_by_major": prereqs_by_major,
                "source": "manual" if not extracted else "scraped",
            }
            save_db(db)
        else:
            db[key] = {
                "name": name,
                "rank": info["rank"],
                "url": info["url"],
                "admissions_url": admissions_url,
                "prereqs_by_major": {},
                "source": "none",
            }
        
        time.sleep(1)  # 礼貌延迟
    
    # 统计
    with_prereqs = sum(1 for v in db.values() if v.get("prereqs_by_major"))
    print(f"\n=== Done ===")
    print(f"Total in DB: {len(db)}")
    print(f"With prereq data: {with_prereqs}")

def apply_to_csv():
    """把爬取到的先修课数据应用到 programs CSV"""
    db = load_existing()
    if not db:
        print("No prereq DB found. Run scrape_top first.")
        return
    
    # 读取并更新
    with open(PROGRAMS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        programs = list(reader)
        fieldnames = reader.fieldnames or []
    
    # 确保有 prerequisite_courses 列
    if "prerequisite_courses" not in fieldnames:
        fieldnames.append("prerequisite_courses")
    
    updated = 0
    for p in programs:
        uni = p["university"].strip()
        major = p["major"]
        rank = int(p.get("rank", 999) or 999)
        
        # 找最匹配的 db 条目
        key = f"{uni}|{rank}"
        entry = db.get(key)
        if not entry:
            # 尝试不包含 rank 的 key
            for k, v in db.items():
                if v["name"] == uni:
                    entry = v
                    break
        
        if entry and entry.get("prereqs_by_major"):
            prereqs = entry["prereqs_by_major"].get(major)
            if not prereqs:
                prereqs = entry["prereqs_by_major"].get("_general")
            if prereqs and not p.get("prerequisite_courses"):
                p["prerequisite_courses"] = prereqs
                updated += 1
    
    dst = PROGRAMS_CSV.replace(".csv", "_with_prereqs.csv")
    with open(dst, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(programs)
    print(f"Written {dst}")
    print(f"Updated {updated} records with prerequisite data")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=50, help="Number of top universities to scrape")
    parser.add_argument("--resume", action="store_true", help="Resume from existing DB")
    parser.add_argument("--apply", action="store_true", help="Apply prereq data to CSV")
    args = parser.parse_args()
    
    if args.apply:
        apply_to_csv()
    else:
        scrape_top(top_n=args.top, resume=args.resume)

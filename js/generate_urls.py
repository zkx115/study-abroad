"""Generate official university website URLs and scrape prerequisite data"""

import csv
import re
import json
import os
import sys
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import time
from typing import Dict, Optional

# ─── 已知高校官网域名（手动维护 Top 200）───────────
KNOWN_DOMAINS = {
    # USA
    "Massachusetts Institute of Technology": "mit.edu",
    "Harvard University": "harvard.edu",
    "Stanford University": "stanford.edu",
    "University of Cambridge": "cam.ac.uk",
    "University of Oxford": "ox.ac.uk",
    "University of California, Berkeley": "berkeley.edu",
    "Imperial College London": "imperial.ac.uk",
    "ETH Zurich": "ethz.ch",
    "University College London": "ucl.ac.uk",
    "Yale University": "yale.edu",
    "University of Chicago": "uchicago.edu",
    "Princeton University": "princeton.edu",
    "Cornell University": "cornell.edu",
    "University of Pennsylvania": "upenn.edu",
    "University of California, Los Angeles": "ucla.edu",
    "University of Washington": "washington.edu",
    "Columbia University": "columbia.edu",
    "Johns Hopkins University": "jhu.edu",
    "University of California, San Diego": "ucsd.edu",
    "University of Michigan-Ann Arbor": "umich.edu",
    "University of Toronto": "utoronto.ca",
    "University of British Columbia": "ubc.ca",
    "McGill University": "mcgill.ca",
    "National University of Singapore": "nus.edu.sg",
    "Nanyang Technological University": "ntu.edu.sg",
    "University of Melbourne": "unimelb.edu.au",
    "University of Sydney": "sydney.edu.au",
    "Australian National University": "anu.edu.au",
    "Seoul National University": "snu.ac.kr",
    "KAIST": "kaist.ac.kr",
    "Tsinghua University": "tsinghua.edu.cn",
    "Peking University": "pku.edu.cn",
    "University of Tokyo": "u-tokyo.ac.jp",
    "Kyoto University": "kyoto-u.ac.jp",
    "Carnegie Mellon University": "cmu.edu",
    "California Institute of Technology": "caltech.edu",
    "University of Illinois Urbana-Champaign": "illinois.edu",
    "Georgia Institute of Technology": "gatech.edu",
    "University of Texas at Austin": "utexas.edu",
    "University of Wisconsin-Madison": "wisc.edu",
    "University of California, Davis": "ucdavis.edu",
    "University of California, Santa Barbara": "ucsb.edu",
    "University of California, Irvine": "uci.edu",
    "University of Southern California": "usc.edu",
    "New York University": "nyu.edu",
    "Northwestern University": "northwestern.edu",
    "Duke University": "duke.edu",
    "University of Minnesota Twin Cities": "umn.edu",
    "University of Maryland, College Park": "umd.edu",
    "Purdue University": "purdue.edu",
    "Ohio State University": "osu.edu",
    "University of Colorado Boulder": "colorado.edu",
    "Michigan State University": "msu.edu",
    "Pennsylvania State University": "psu.edu",
    "Texas A&M University": "tamu.edu",
    "University of Florida": "ufl.edu",
    "University of Arizona": "arizona.edu",
    "Arizona State University": "asu.edu",
    "Rice University": "rice.edu",
    "University of Rochester": "rochester.edu",
    "Boston University": "bu.edu",
    "University of Notre Dame": "nd.edu",
    "University of Virginia": "virginia.edu",
    "Tufts University": "tufts.edu",
    "Vanderbilt University": "vanderbilt.edu",
    "University of Pittsburgh": "pitt.edu",
    "Rutgers University": "rutgers.edu",
    "Indiana University Bloomington": "indiana.edu",
    "University of Iowa": "uiowa.edu",
    "University of Utah": "utah.edu",
    "University of Kansas": "ku.edu",
    "University of Oregon": "uoregon.edu",
    "Washington University in St. Louis": "wustl.edu",
    "Dartmouth College": "dartmouth.edu",
    "Brown University": "brown.edu",
    "University of California, Santa Cruz": "ucsc.edu",
    "North Carolina State University": "ncsu.edu",
    "University of North Carolina": "unc.edu",
    "University of Connecticut": "uconn.edu",
    "University of Miami": "miami.edu",
    "Emory University": "emory.edu",
    "Georgetown University": "georgetown.edu",
    "University of Texas Dallas": "utdallas.edu",
    "Virginia Tech": "vt.edu",
    "University of Hawaii at Manoa": "hawaii.edu",
    "University of Nebraska-Lincoln": "unl.edu",
    "University of Alabama": "ua.edu",
    "University of Kentucky": "uky.edu",
    "University of Tennessee": "utk.edu",
    "University of South Carolina": "sc.edu",
    "University of Missouri": "missouri.edu",
    "University of Oklahoma": "ou.edu",
    "University of Mississippi": "olemiss.edu",
    "University of Arkansas": "uark.edu",
    "University of Vermont": "uvm.edu",
    "University of New Hampshire": "unh.edu",
    "University of Maine": "umaine.edu",
    "University of Rhode Island": "uri.edu",
    "University of Delaware": "udel.edu",
    "University of Wyoming": "uwyo.edu",
    "University of Montana": "umt.edu",
    "University of Idaho": "uidaho.edu",
    "University of Alaska Fairbanks": "alaska.edu",
    "University of Nevada, Las Vegas": "unlv.edu",
    "University of Nevada, Reno": "unr.edu",
    "University of New Mexico": "unm.edu",
    "University of North Dakota": "und.edu",
    "University of South Dakota": "usd.edu",
    "University of Utah": "utah.edu",
    "University of Wisconsin-Milwaukee": "uwm.edu",
    # UK
    "University of Edinburgh": "ed.ac.uk",
    "University of Manchester": "manchester.ac.uk",
    "King's College London": "kcl.ac.uk",
    "London School of Economics": "lse.ac.uk",
    "University of Bristol": "bristol.ac.uk",
    "University of Glasgow": "gla.ac.uk",
    "University of Birmingham": "bham.ac.uk",
    "University of Southampton": "soton.ac.uk",
    "University of Leeds": "leeds.ac.uk",
    "University of Sheffield": "sheffield.ac.uk",
    "University of Nottingham": "nottingham.ac.uk",
    "University of Warwick": "warwick.ac.uk",
    "University of St Andrews": "st-andrews.ac.uk",
    "University of York": "york.ac.uk",
    "Durham University": "durham.ac.uk",
    "University of Liverpool": "liverpool.ac.uk",
    "University of Leicester": "le.ac.uk",
    "University of Aberdeen": "abdn.ac.uk",
    "University of Reading": "reading.ac.uk",
    "Queen Mary University of London": "qmul.ac.uk",
    "Cardiff University": "cardiff.ac.uk",
    "University of East Anglia": "uea.ac.uk",
    "University of Exeter": "exeter.ac.uk",
    "University of Bath": "bath.ac.uk",
    "Loughborough University": "lboro.ac.uk",
    "University of Surrey": "surrey.ac.uk",
    "Royal Holloway": "royalholloway.ac.uk",
    "University of Dundee": "dundee.ac.uk",
    "University of Strathclyde": "strath.ac.uk",
    "University of Kent": "kent.ac.uk",
    "University of Stirling": "stir.ac.uk",
    "University of Essex": "essex.ac.uk",
    "University of Sussex": "sussex.ac.uk",
    "Aston University": "aston.ac.uk",
    "Brunel University": "brunel.ac.uk",
    "City University London": "city.ac.uk",
    "University of Hull": "hull.ac.uk",
    "University of Bradford": "bradford.ac.uk",
    "University of Portsmouth": "port.ac.uk",
    "University of Salford": "salford.ac.uk",
    # China
    "Zhejiang University": "zju.edu.cn",
    "Fudan University": "fudan.edu.cn",
    "Shanghai Jiao Tong University": "sjtu.edu.cn",
    "University of Science and Technology of China": "ustc.edu.cn",
    "Nanjing University": "nju.edu.cn",
    "Wuhan University": "whu.edu.cn",
    "Huazhong University of Science and Technology": "hust.edu.cn",
    "Sun Yat-sen University": "sysu.edu.cn",
    "Harbin Institute of Technology": "hit.edu.cn",
    "Xi'an Jiaotong University": "xjtu.edu.cn",
    # Australia
    "University of Queensland": "uq.edu.au",
    "UNSW Sydney": "unsw.edu.au",
    "Monash University": "monash.edu",
    "University of Western Australia": "uwa.edu.au",
    "University of Adelaide": "adelaide.edu.au",
    "University of Technology Sydney": "uts.edu.au",
    "RMIT University": "rmit.edu.au",
    # Hong Kong
    "University of Hong Kong": "hku.hk",
    "Chinese University of Hong Kong": "cuhk.edu.hk",
    "Hong Kong University of Science and Technology": "hkust.edu.hk",
    "Hong Kong Polytechnic University": "polyu.edu.hk",
    "City University of Hong Kong": "cityu.edu.hk",
    "Hong Kong Baptist University": "hkbu.edu.hk",
    # Germany
    "Technical University of Munich": "tum.de",
    "LMU Munich": "lmu.de",
    "Heidelberg University": "uni-heidelberg.de",
    "Humboldt University of Berlin": "hu-berlin.de",
    "Free University of Berlin": "fu-berlin.de",
    "RWTH Aachen University": "rwth-aachen.de",
    "Karlsruhe Institute of Technology": "kit.edu",
    # France
    "Sorbonne University": "sorbonne-universite.fr",
    "Université PSL": "psl.eu",
    "Institut Polytechnique de Paris": "ip-paris.fr",
    # Netherlands
    "Delft University of Technology": "tudelft.nl",
    "University of Amsterdam": "uva.nl",
    "Utrecht University": "uu.nl",
    "Leiden University": "leidenuniv.nl",
    "Erasmus University Rotterdam": "eur.nl",
    "University of Groningen": "rug.nl",
    "Wageningen University & Research": "wur.nl",
    # Japan  
    "Tokyo Institute of Technology": "titech.ac.jp",
    "Osaka University": "osaka-u.ac.jp",
    "Tohoku University": "tohoku.ac.jp",
    "Nagoya University": "nagoya-u.ac.jp",
    "Kyushu University": "kyushu-u.ac.jp",
    "Hokkaido University": "hokudai.ac.jp",
    # Switzerland
    "EPFL": "epfl.ch",
    "University of Zurich": "uzh.ch",
    "University of Bern": "unibe.ch",
    # Sweden
    "KTH Royal Institute of Technology": "kth.se",
    "Lund University": "lu.se",
    "Uppsala University": "uu.se",
    "Chalmers University of Technology": "chalmers.se",
    "Stockholm University": "su.se",
    # Denmark
    "University of Copenhagen": "ku.dk",
    "Technical University of Denmark": "dtu.dk",
    "Aarhus University": "au.dk",
    # Finland
    "University of Helsinki": "helsinki.fi",
    "Aalto University": "aalto.fi",
    # Norway
    "University of Oslo": "uio.no",
    "Norwegian University of Science and Technology": "ntnu.no",
    # Belgium
    "KU Leuven": "kuleuven.be",
    "Ghent University": "ugent.be",
    # Italy
    "Politecnico di Milano": "polimi.it",
    "University of Bologna": "unibo.it",
    "Sapienza University of Rome": "uniroma1.it",
    # Spain
    "University of Barcelona": "ub.edu",
    "Autonomous University of Madrid": "uam.es",
    "Complutense University of Madrid": "ucm.es",
    # Ireland
    "Trinity College Dublin": "tcd.ie",
    "University College Dublin": "ucd.ie",
    # New Zealand
    "University of Auckland": "auckland.ac.nz",
    "University of Otago": "otago.ac.nz",
    # South Korea
    "Yonsei University": "yonsei.ac.kr",
    "Korea University": "korea.ac.kr",
    "Sungkyunkwan University": "skku.edu",
    # India
    "Indian Institute of Technology Bombay": "iitb.ac.in",
    "Indian Institute of Technology Delhi": "iitd.ac.in",
    "Indian Institute of Technology Madras": "iitm.ac.in",
    "Indian Institute of Science": "iisc.ac.in",
    # Russia
    "Lomonosov Moscow State University": "msu.ru",
    # Saudi Arabia
    "King Abdullah University of Science and Technology": "kaust.edu.sa",
    # Taiwan
    "National Taiwan University": "ntu.edu.tw",
    "National Tsing Hua University": "nthu.edu.tw",
    "National Yang Ming Chiao Tung University": "nycu.edu.tw",
    # Brazil
    "University of São Paulo": "usp.br",
    "State University of Campinas": "unicamp.br",
    # Singapore
    "Singapore Management University": "smu.edu.sg",
    # Others - add more as needed
}

# ─── TLD 按国家映射 ───────────────────
COUNTRY_TLDS = {
    "United States": "edu", "United Kingdom": "ac.uk", "Canada": "ca",
    "Australia": "edu.au", "New Zealand": "ac.nz", "Germany": "de",
    "France": "fr", "Netherlands": "nl", "Switzerland": "ch",
    "Sweden": "se", "Denmark": "dk", "Finland": "fi", "Norway": "no",
    "Belgium": "be", "Italy": "it", "Spain": "es", "Ireland": "ie",
    "Japan": "ac.jp", "South Korea": "ac.kr", "China": "edu.cn",
    "Hong Kong": "edu.hk", "Taiwan": "edu.tw", "India": "ac.in",
    "Singapore": "edu.sg", "Saudi Arabia": "edu.sa", "Russia": "ru",
    "Brazil": "br",
}

def guess_domain(name: str, country: str) -> str:
    """根据大学名称猜测官网域名"""
    n = name.lower().strip()
    # 去除括号内容
    n = re.sub(r'\s*\(.*?\)', '', n).strip()
    # 转 slug — 取关键单词
    n = re.sub(r'[^a-z0-9\s]', '', n)
    # 处理常见模式
    replacements = [
        (r'^university of\s+', ''),
        (r'\s+university$', ''),
        (r'\s+institute of technology$', ''),
        (r'\s+institute of\s+', ''),
        (r'\s+college$', ''),
        (r'\s+school of\s+', ''),
        (r'\s+academy$', ''),
        (r'\s+polytechnic$', ''),
    ]
    slug = n
    for pattern, replacement in replacements:
        slug = re.sub(pattern, replacement, slug)
    slug = slug.replace(' ', '').replace('-', '')[:30]
    if not slug:
        slug = n.replace(' ', '')[:30]
    
    tld = COUNTRY_TLDS.get(country, "edu")
    return f"{slug}.{tld}"

def normalize_uni_name(name: str) -> str:
    """标准化大学名称：去除括号等干扰"""
    n = name.strip()
    n = re.sub(r'\s*\(.*?\)\s*', '', n).strip()
    return n

def generate_homepage_url(name: str, country: str) -> str:
    """生成大学官网首页 URL"""
    name_clean = normalize_uni_name(name)
    domain = KNOWN_DOMAINS.get(name_clean)
    if not domain:
        domain = guess_domain(name_clean, country)
    return f"https://www.{domain}"

# ─── 爬取先修课数据 ──────────────────
def scrape_prerequisites(url: str, program_name: str, timeout: int = 10) -> Optional[str]:
    """
    尝试从大学官网爬取专业的先修课要求。
    返回先修课字符串（分号分隔），或 None
    """
    # 常见 admissions 路径
    admissions_paths = [
        "/admissions", "/graduate/admissions", "/grad/admissions",
        "/admission", "/graduate-admissions", "/apply",
        "/programs/graduate", "/graduate/programs",
        "/academics/graduate", "/future-students/graduate",
    ]
    
    slug = program_name.lower().replace(' ', '-').replace(',', '')
    
    for path in admissions_paths:
        target = url.rstrip('/') + path
        try:
            r = requests.get(target, timeout=timeout, 
                           headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                text = soup.get_text().lower()
                # 寻找先修课相关的段落
                prereq_keywords = ["prerequisite", "prerequisites", "prerequisite courses",
                                 "prerequisite course", "prerequisite knowledge",
                                 "admission requirements", "entry requirements",
                                 "先修课", "先修课程", "入学要求"]
                found = [kw for kw in prereq_keywords if kw in text]
                if found:
                    # 尝试提取先修课列表
                    for kw in found:
                        # 找到关键词附近的段落
                        paragraphs = soup.find_all(['p', 'li', 'div'])
                        for p in paragraphs:
                            if kw in p.get_text().lower():
                                txt = p.get_text().strip()
                                if len(txt) > 20 and len(txt) < 500:
                                    return txt[:300]
            time.sleep(0.5)
        except Exception as e:
            pass
    return None

# ─── 主流程 ──────────────────────────
def main():
    src = os.path.join(os.path.dirname(__file__), 
                       "../../workspace/university_db/programs.csv")
    dst = os.path.join(os.path.dirname(__file__),
                       "../../workspace/university_db/programs_v2.csv")
    
    # 1. 读取原始数据
    with open(src, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        programs = list(reader)
    
    print(f"读取 {len(programs)} 条记录")
    
    # 2. 生成官网 URL
    url_cache = {}
    updated = 0
    for p in programs:
        uni = p["university"].strip()
        if uni not in url_cache:
            url_cache[uni] = generate_homepage_url(uni, p.get("country", ""))
        
        old_url = p.get("program_url", "")
        new_url = url_cache[uni]
        p["program_url"] = new_url
        if old_url != new_url:
            updated += 1
    
    print(f"已更新 {updated} 条 program_url（QS路径 → 官网首页）")
    
    # 3. 写入新 CSV
    with open(dst, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=programs[0].keys())
        writer.writeheader()
        writer.writerows(programs)
    
    print(f"写入 {dst}")
    
    # 4. 输出统计
    total_unis = len(set(p["university"].strip() for p in programs))
    known = sum(1 for u in set(p["university"].strip() for p in programs) 
                if u in KNOWN_DOMAINS)
    print(f"总院校数: {total_unis}")
    print(f"已知域名（精确匹配）: {known}")
    print(f"启发式猜测: {total_unis - known}")

if __name__ == "__main__":
    main()

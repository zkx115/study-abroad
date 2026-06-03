"""Convert programs.csv to compact JS array for GitHub Pages"""

import csv
import json
import os
import re

SRC = os.path.join(os.path.dirname(__file__), "../../workspace/university_db/programs_v2.csv")
DST = os.path.join(os.path.dirname(__file__), "programs.js")

# 字段别名缩短（节省大小）
SHORT = {
    "university": "u", "university_zh": "z", "major": "m", "country": "c",
    "rank": "r", "qs_rank": "q", "the_rank": "t", "city": "y",
    "min_gpa": "g", "min_language_ielts": "i", "min_language_toefl": "f",
    "require_gre": "gr", "tuition_usd": "tu", "living_cost_usd": "lv",
    "study_length_years": "sl", "post_study_work_visa_months": "vw",
    "international_student_ratio": "is", "median_salary_3yr_usd": "ms",
    "admit_rate": "ar", "student_count": "sc",
    "academic_reputation": "ac", "employer_reputation": "er",
    "overall_score": "os", "program_url": "pu", "data_source": "ds",
}

with open(SRC, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    records = []
    for row in reader:
        rec = {}
        for long_key, short_key in SHORT.items():
            val = row.get(long_key, "").strip()
            if val:
                rec[short_key] = val
        records.append(rec)

# 写为紧凑格式
with open(DST, "w", encoding="utf-8") as f:
    f.write("// Auto-generated from programs.csv. Do not edit.\n")
    f.write(f"const PROGRAMS = ")
    f.write(json.dumps(records, ensure_ascii=False, separators=(",", ":")))
    f.write(";\n")

size_kb = os.path.getsize(DST) / 1024
print(f"Written {DST}")
print(f"Records: {len(records)}")
print(f"Size: {size_kb:.0f} KB")

"""Conservative, offline extraction of explicitly present resume fields."""

import re
import unicodedata


def extract_resume_profile(text):
    text = unicodedata.normalize("NFKC", str(text or ""))
    name = re.search(
        r"(?:^|[\n|｜【])\s*(?:姓名|Name)\s*[:：]\s*"
        r"([\u4e00-\u9fff·]{2,20}|[A-Za-z][A-Za-z .'-]{1,79})[ \t]*(?=$|[\n|｜】])",
        text, re.MULTILINE | re.IGNORECASE,
    )
    phone = re.search(r"(?<!\d)(1[3-9]\d[- \t]?\d{4}[- \t]?\d{4})(?!\d)", text)
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    education = re.search(
        r"(?:最高学历|学历|学位)\s*[:：]\s*(博士|硕士|本科|学士|大专|专科|高中|中专)(?!优先|项目|导师)",
        text,
    )
    name_value = name.group(1).strip() if name else ""
    header = text.lstrip().split("\n")[0].strip()
    bilingual_header = re.fullmatch(r"([\u4e00-\u9fff·]{2,4})[ \t]+[A-Za-z][A-Za-z .'-]+", header)
    if not name_value and bilingual_header and re.search(r"@|1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}", text[:500]):
        name_value = bilingual_header.group(1)
    education_value = education.group(1) if education else ""
    section = re.search(
        r"(?:教育经历|教育背景|EDUCATION)([\s\S]*?)(?=实习经历|工作经历|项目经历|INTERNSHIP|WORK EXPERIENCE|$)",
        text, re.IGNORECASE,
    )
    if not education_value and section:
        for degree in ("博士", "硕士", "本科", "学士", "大专", "专科", "高中", "中专"):
            if re.search(degree + r"(?!优先|项目|导师)", section.group(1)):
                enrolled = re.search(degree + r"(?:研究生)?\s*[（(]?\s*在读", section.group(1))
                education_value = degree + ("（在读）" if enrolled else "")
                break
    return {
        "name": name_value,
        "phone": re.sub(r"[- \t]", "", phone.group(1)) if phone else "",
        "email": email.group(0) if email else "",
        "exp": education_value,
    }

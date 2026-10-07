ROLE_FAMILIES = {
    "技術營業/Pre-sales": [
        "기술영업", "technical sales", "pre-sales", "presales",
        "솔루션 세일즈", "solution sales", "se ", "sales engineer",
    ],
    "解決方案顧問": [
        "솔루션", "solution", "컨설턴트", "consultant", "advisory",
        "컨설팅", "consulting",
    ],
    "BD/事業開發": [
        "사업개발", "business development", "bd ", "파트너십",
        "partnership", "제휴", "alliance",
    ],
    "客戶成功/CS": [
        "고객성공", "customer success", "csm", "고객관리",
        "account management", "customer experience",
    ],
    "UX Research": [
        "ux", "리서치", "research", "사용자 연구",
        "user research", "usability",
    ],
    "數據分析": [
        "데이터", "data", "분석", "analyst", "analytics",
        "bi ", "business intelligence",
    ],
    "行銷": [
        "마케팅", "marketing", "pmm", "product marketing",
        "콘텐츠", "content", "growth", "그로스",
    ],
    "PM/기획": [
        "기획", "planner", "product manager", "pm ",
        "프로덕트", "product owner",
    ],
    "其他": [],
}


def classify_role(title: str) -> str:
    title_lower = title.lower()
    for family, keywords in ROLE_FAMILIES.items():
        if family == "其他":
            continue
        for kw in keywords:
            if kw in title_lower:
                return family
    return "其他"

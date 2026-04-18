import re
from urllib.parse import urlparse


# URL 카테고리별 패턴 정의
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "government": [r"\.go\.kr", r"\.gov\.", r"\.mil\.kr", r"정부", r"공공", r"\.or\.kr/.*공공"],
    "finance": [r"\.kbstar\.", r"\.shinhan\.", r"\.toss\.", r"\.hanabank\.", r"\.wooribank\.",
                r"금융", r"bank", r"\.fnguide\.", r"\.kisrating\.", r"finance\."],
    "news": [r"\.chosun\.", r"\.joongang\.", r"\.donga\.", r"\.hani\.", r"news\.",
             r"\.media\.", r"\.newsis\.", r"\.yonhap\.", r"\.yna\.co\.kr"],
    "portal": [r"naver\.com", r"daum\.net", r"kakao\.com", r"zum\.com"],
    "sns": [r"instagram\.", r"twitter\.", r"facebook\.", r"x\.com", r"tiktok\.",
            r"youtube\.", r"linkedin\."],
    "ecommerce": [r"coupang\.", r"11st\.", r"gmarket\.", r"auction\.", r"interpark\.",
                  r"shop", r"mall\.", r"store\.", r"\.co\.kr/shop", r"ssg\.com", r"lotte\.com"],
}

# 카테고리별 기본 파이프라인 실행 순서 (1=API, 2=HTTP, 3=Stealth, 4=AI, 5=Proxy)
CATEGORY_PIPELINE_ORDER: dict[str, list[int]] = {
    "government": [1, 2, 3],      # 공공 API 풍부, 정적 HTML 위주
    "finance":    [1],             # 법적 규제로 API만 허용
    "news":       [1, 2, 4],       # SSR 기반, RSS 피드, 구조 변경 잦음
    "portal":     [1, 3, 4, 5],    # 강력한 안티봇, SPA 기반
    "sns":        [1],             # 법적/ToS 제약, API만 허용
    "ecommerce":  [1, 3, 4, 5],    # 강력한 안티봇, SEO용 일부 SSR
    "enterprise": [2, 4, 3],       # 주로 정적/WordPress 기반
}


def classify_url(url: str) -> str:
    """URL을 카테고리로 자동 분류합니다."""
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return category
    return "enterprise"


def get_pipeline_order(category: str) -> list[int]:
    """카테고리별 파이프라인 실행 순서를 반환합니다."""
    return CATEGORY_PIPELINE_ORDER.get(category, CATEGORY_PIPELINE_ORDER["enterprise"])


def extract_domain(url: str) -> str:
    """URL에서 도메인을 추출합니다."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""

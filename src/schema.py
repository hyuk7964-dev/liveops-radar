"""LIVEOPS RADAR CSV 스키마. 열 이름과 허용 값은 여기 한 곳에서만 고친다.

기준: LIVEOPS_RADAR_PROJECT_BRIEF.md 6장. 브리프와 다른 점은 DATA_DICTIONARY.md '브리프 대비 변경' 참고.
"""

REGIONS = {'KR', 'JP', 'GLOBAL'}
STORES = {'google_play', 'app_store', 'steam', 'gamerch'}  # gamerch = 일본 커뮤니티(스토어 아님)
LANGS = {'ko', 'ja', 'en', 'other', 'unknown'}
METHODS = {'steam_official_api', 'apple_rss', 'community_lowrate', 'appfollow_api', 'appfollow_export', 'manual_csv', 'manual_input', 'synthetic'}
UPDATE_TYPES = {'content', 'character', 'event', 'balance', 'monetization', 'bugfix',
                'maintenance', 'system', 'developer_note', 'other'}

# (열 이름, 필수 여부)
REVIEW_COLUMNS = [
    ('review_id', True), ('source_review_id', False), ('game_id', True), ('service_region', True),
    ('store', True), ('store_country', False), ('language', True), ('source_language_label', False),
    ('review_date', True), ('collected_at', True), ('rating', False), ('recommended', False),
    ('review_title', False), ('review_text', True), ('app_version', False), ('developer_reply', False),
    ('votes_up', False), ('playtime_at_review_min', False), ('source_url', True),
    ('collection_method', True), ('data_permission_note', True), ('is_synthetic', True),
    ('date_precision', False),  # 빈 값 = 정확한 날짜, day / month = 상대 표기(예: 14日まえ)에서 환산
]

UPDATE_COLUMNS = [
    ('update_id', True), ('game_id', True), ('service_region', True), ('update_date', False),
    ('notice_date', True), ('version', False), ('update_type', True), ('update_title', True),
    ('update_description', False), ('source_url', True), ('language', True), ('collected_at', True),
    ('collection_method', True), ('is_synthetic', True),
]

REVIEW_FIELDS = [c for c, _ in REVIEW_COLUMNS]
UPDATE_FIELDS = [c for c, _ in UPDATE_COLUMNS]


def detect_language(text):
    """본문 글자로 언어를 추정한다(국가 정보는 쓰지 않는다). 가나가 있으면 ja, 한글이 많으면 ko, 라틴 문자가 많으면 en."""
    t = [ch for ch in text if not ch.isspace()]
    if not t:
        return 'unknown'
    kana = sum('぀' <= ch <= 'ヿ' for ch in t)
    hangul = sum('가' <= ch <= '힣' or 'ㄱ' <= ch <= 'ㆎ' for ch in t)
    latin = sum(ch.isascii() and ch.isalpha() for ch in t)
    if kana >= 2:
        return 'ja'
    if hangul >= max(1, latin) and hangul / len(t) >= 0.2:
        return 'ko'
    if latin / len(t) >= 0.5:
        return 'en'
    if not any(ch.isalpha() for ch in t):
        return 'unknown'  # 이모지 · 기호 · 숫자만 있는 글
    return 'other'  # 중국어 · 태국어 등

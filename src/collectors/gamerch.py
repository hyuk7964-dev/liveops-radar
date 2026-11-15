"""Gamerch 블루 아카이브 공략wiki 게시판 수집기 (일본 커뮤니티 보조 자료).

- 대상: 不具合・バグの報告掲示板(219513), 雑談掲示板(219515)
- 이용 조건: Gamerch 이용약관에 자동 수집 금지 조항 없음. 글 이용권은 Gamerch에만 허락 → 원문 재배포 금지,
  화면에는 200자 이내 발췌와 원문 링크만. 비상업 포트폴리오. 2026-11-08 사용자 승인.
- 부하: 쪽마다 3초 쉼. 작성자 이름 · ID는 저장하지 않는다.
- 날짜: 목록에는 "14日まえ" "3カ月まえ" 같은 상대 표기만 있다. 수집일 기준으로 환산하고 date_precision에 정밀도를 남긴다.

사용: python -m src.collectors.gamerch --days 180
"""
import argparse, html, os, re, sys, time, urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.schema import REVIEW_FIELDS, detect_language
from src.collectors.steam import write, log, now, ROOT

BOARDS = {'219513': 'bug_report', '219515': 'chat'}
PERMISSION = 'Gamerch 게시판. 자동 수집 금지 조항 없음, 글 이용권은 Gamerch에만 허락. 저속 · 비상업 · 재배포 없음 · 발췌만. 사용자 승인'
ITEM = re.compile(r'<li class="thread-li">.*?tb__comment-number">\s*(\d+)\s*</div>.*?tb__date-id">\s*([^<]+?)\s*<span>.*?<p>(.*?)</p>', re.S)


def rel_date(s, today):
    """'14日まえ' → (날짜, 'day'), '3カ月まえ' → (날짜, 'month'). 모르면 (None, None)."""
    for pat, unit in ((r'(\d+)\s*分', 'min'), (r'(\d+)\s*時間', 'hour'), (r'(\d+)\s*日', 'day'), (r'(\d+)\s*カ月', 'month'), (r'(\d+)\s*年', 'year')):
        m = re.search(pat, s)
        if m:
            n = int(m.group(1))
            days = {'min': 0, 'hour': 0, 'day': n, 'month': n * 30, 'year': n * 365}[unit]
            return today - timedelta(days=days), ('day' if unit in ('min', 'hour', 'day') else unit)
    return None, None


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (liveops-radar portfolio)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'ignore')


def collect(days):
    today, ts, out = datetime.now(), now(), []
    for bid, kind in BOARDS.items():
        for page in range(1, 60):
            h = fetch(f'https://gamerch.com/bluearchive/{bid}?comment_page={page}')
            items = ITEM.findall(h)
            if not items:
                break
            old = 0
            for num, rel, body in items:
                d, prec = rel_date(rel, today)
                text = html.unescape(re.sub(r'<br\s*/?>', '\n', body))
                text = re.sub(r'<[^>]+>', '', text).strip()
                if d is None or (today - d).days > days:
                    old += 1
                    continue
                out.append({
                    'review_id': f'gamerch_{bid}_{num}', 'source_review_id': num, 'game_id': 'blue_archive',
                    'service_region': 'JP', 'store': 'gamerch', 'store_country': 'JP',
                    'language': detect_language(text), 'source_language_label': kind,
                    'review_date': d.strftime('%Y-%m-%d'), 'collected_at': ts, 'rating': '', 'recommended': '',
                    'review_title': '', 'review_text': text, 'app_version': '', 'developer_reply': '',
                    'votes_up': '', 'playtime_at_review_min': '',
                    'source_url': f'https://gamerch.com/bluearchive/entry/{bid}/comment/{num}',
                    'collection_method': 'community_lowrate', 'data_permission_note': PERMISSION,
                    'is_synthetic': 'False', 'date_precision': prec})
            if old == len(items):  # 이 쪽이 모두 기간 밖이면 멈춘다(새 글 순)
                break
            time.sleep(3)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=180); a = ap.parse_args()
    rows = collect(a.days)
    path = os.path.join(ROOT, 'data', 'raw', 'reviews', f'gamerch_jp_{datetime.now():%Y%m%d}.csv')
    write(path, REVIEW_FIELDS, rows)
    log('gamerch_jp', 'community_lowrate', len(rows), a.days, 'Gamerch 불구합 · 잡담 게시판. 날짜는 상대 표기 환산', 'user_approved_no_prohibition')
    print(path, len(rows))

"""앱스토어 고객 리뷰 RSS 수집기 (KR · JP · US).

- 출처: itunes.apple.com/<국가>/rss/customerreviews (Apple 공개 피드, 최신순 최대 10쪽 x 50건)
- 이용 조건: Apple 공식 문서 · 약관 미발견. 2026-11-08 사용자 승인으로 사용(DATA_SOURCE_POLICY 2장).
  조건 = 저속 수집(쪽당 2초) · 비상업 포트폴리오 분석 · 원문 재배포 없음 · 화면에는 200자 이내 발췌와 링크.
- 작성자 이름은 저장하지 않는다. 피드가 가끔 빈 쪽을 주므로 쪽마다 3번까지 다시 시도한다.

사용: python -m src.collectors.apple_rss kr|jp|us
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.schema import REVIEW_FIELDS, detect_language
from src.collectors.steam import write, log, now, ROOT

APPS = {'kr': ('1571873795', 'GLOBAL'), 'us': ('1571873795', 'GLOBAL'), 'jp': ('1515877221', 'JP')}
PERMISSION = 'Apple 공개 RSS. 공식 약관 미발견, 사용자 승인(2026-11-08). 저속 · 비상업 · 원문 재배포 없음 · 발췌만 표시'


def page(cc, app, p):
    url = f'https://itunes.apple.com/{cc}/rss/customerreviews/page={p}/id={app}/sortby=mostrecent/json'
    for attempt in range(8):  # 피드가 빈 쪽을 자주 돌려줘 여러 번 다시 시도
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'liveops-radar-portfolio/0.1'}), timeout=30) as r:
                e = json.load(r)['feed'].get('entry', [])
            e = [x for x in (e if isinstance(e, list) else [e]) if 'im:rating' in x]
            if e:
                return e
        except Exception as ex:
            print('retry', cc, p, ex)
        time.sleep(5)
    return []


def collect(cc):
    app, region = APPS[cc]
    out, seen, ts = [], set(), now()
    for p in range(1, 11):
        for x in page(cc, app, p):
            rid = x['id']['label']
            if rid in seen:
                continue
            seen.add(rid)
            text = x['content']['label']
            out.append({
                'review_id': f'appstore_{cc}_{rid}', 'source_review_id': rid, 'game_id': 'blue_archive',
                'service_region': region, 'store': 'app_store', 'store_country': cc.upper(),
                'language': detect_language(x['title']['label'] + ' ' + text), 'source_language_label': '',
                'review_date': x['updated']['label'][:10], 'collected_at': ts, 'rating': x['im:rating']['label'],
                'recommended': '', 'review_title': x['title']['label'], 'review_text': text,
                'app_version': x.get('im:version', {}).get('label', ''), 'developer_reply': '',
                'votes_up': x.get('im:voteSum', {}).get('label', ''), 'playtime_at_review_min': '',
                'source_url': f'https://apps.apple.com/{cc}/app/id{app}?see-all=reviews',
                'collection_method': 'apple_rss', 'data_permission_note': PERMISSION, 'is_synthetic': 'False'})
        time.sleep(2)
    return out


if __name__ == '__main__':
    cc = sys.argv[1]
    rows = collect(cc)
    stamp = datetime.now().strftime('%Y%m%d')
    path = os.path.join(ROOT, 'data', 'raw', 'reviews', f'appstore_{cc}_{stamp}.csv')
    if os.path.exists(path):  # 같은 날 다시 돌리면 기존 행과 합친다(피드가 쪽을 빠뜨리는 문제 보완)
        import csv
        old = list(csv.DictReader(open(path, encoding='utf-8-sig')))
        ids = {r['review_id'] for r in rows}
        rows += [r for r in old if r['review_id'] not in ids]
    write(path, REVIEW_FIELDS, rows)
    days = (datetime.now(timezone.utc) - datetime.fromisoformat(min(r['review_date'] for r in rows))
            .replace(tzinfo=timezone.utc)).days if rows else 0
    log(f'appstore_reviews_{cc}', 'apple_rss', len(rows), days, 'Apple 공개 RSS 최신순 최대 500건', 'user_approved_terms_unverified')
    print(path, len(rows), (min(r['review_date'] for r in rows), max(r['review_date'] for r in rows)) if rows else '')

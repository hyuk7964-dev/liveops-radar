"""Steam 공식 Web API 수집기 (리뷰 + 뉴스).

- 리뷰: IUserReviewsService/GetAppReviews v1 (키 없이 호출 가능, 공식 문서 partner.steamgames.com/doc/webapi/IUserReviewsService)
- 뉴스: ISteamNews/GetNewsForApp v2
- 이용 조건: Steam Web API Terms of Use (steamcommunity.com/dev/apiterms) 하루 100,000회 이하, Valve 제휴처럼 보이게 표시 금지.
- 작성자 steamid는 저장하지 않는다(개인 식별 정보 최소화).

사용:
  python -m src.collectors.steam reviews --lang koreana --days 90
  python -m src.collectors.steam news --days 90
"""
import argparse, csv, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.schema import REVIEW_FIELDS, UPDATE_FIELDS, detect_language

APPID = 3557620  # 블루 아카이브 Steam (글로벌, 넥슨) — 모바일과 다른 모집단
GAME = 'blue_archive'
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
PERMISSION = 'Steam 공식 API(키 없음). Steam Web API ToU 2010-07. 분석 저장 허용 범위 내 사용, 웹 표시는 발췌만, 원문 재배포 안 함'
UA = {'User-Agent': 'liveops-radar-portfolio/0.1'}


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def reviews(lang, days):
    end = int(time.time()); start = end - days * 86400
    cursor, out, seen = '*', [], set()
    while True:
        q = {'appid': APPID, 'filter': 1, 'languages[0]': lang, 'num_per_page': 100, 'review_type': 0,
             'purchase_type': 1, 'date_range_start': start, 'date_range_end': end, 'cursor': cursor}
        r = get('https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/?' + urllib.parse.urlencode(q))
        r = r.get('response', r)
        page = [x for x in r.get('reviews', []) if x['recommendationid'] not in seen]
        if not page:
            break
        ts = now()
        for x in page:
            seen.add(x['recommendationid'])
            out.append({
                'review_id': f"steam_{x['recommendationid']}", 'source_review_id': x['recommendationid'],
                'game_id': GAME, 'service_region': 'GLOBAL', 'store': 'steam', 'store_country': '',
                'language': detect_language(x['review']), 'source_language_label': x['language'],
                'review_date': datetime.fromtimestamp(x['timestamp_created'], timezone.utc).strftime('%Y-%m-%d'),
                'collected_at': ts, 'rating': '', 'recommended': str(bool(x['voted_up'])),
                'review_title': '', 'review_text': x['review'], 'app_version': '',
                'developer_reply': x.get('developer_response', ''), 'votes_up': x.get('votes_up', ''),
                'playtime_at_review_min': x.get('author', {}).get('playtime_at_review', ''),
                'source_url': f"https://steamcommunity.com/app/{APPID}/reviews/",
                'collection_method': 'steam_official_api', 'data_permission_note': PERMISSION, 'is_synthetic': 'False'})
        cursor = r.get('cursor')
        if not cursor:
            break
        time.sleep(1)
    return out


def news(days):
    since = time.time() - days * 86400
    d = get(f'https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={APPID}&count=100&maxlength=400')
    ts, out = now(), []
    for n in d['appnews']['newsitems']:
        if n['date'] < since:
            continue
        out.append({
            'update_id': f"steamnews_{n['gid']}", 'game_id': GAME, 'service_region': 'GLOBAL', 'update_date': '',
            'notice_date': datetime.fromtimestamp(n['date'], timezone.utc).strftime('%Y-%m-%d'), 'version': '',
            'update_type': 'other', 'update_title': n['title'], 'update_description': n.get('contents', '')[:400],
            'source_url': n['url'], 'language': detect_language(n['title']), 'collected_at': ts,
            'collection_method': 'steam_official_api', 'is_synthetic': 'False'})
    return out  # update_type은 사람이 분류하기 전까지 other


def write(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def log(source, method, n, days, note, permission='official_api_terms_reviewed'):
    p = os.path.join(ROOT, 'data', 'processed', 'data_collection_log.csv')
    new = not os.path.exists(p)
    with open(p, 'a', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['collection_id', 'source_name', 'source_type', 'collected_at', 'date_from', 'date_to',
                        'records_collected', 'records_rejected', 'collection_method', 'permission_status', 'notes'])
        t = time.time()
        w.writerow([f'c{int(t)}', source, 'reviews' if 'review' in source else 'updates', now(),
                    datetime.fromtimestamp(t - days * 86400, timezone.utc).strftime('%Y-%m-%d'),
                    datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%d'), n, 0, method,
                    permission, note])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['reviews', 'news'])
    ap.add_argument('--lang', default='koreana')
    ap.add_argument('--days', type=int, default=90)
    a = ap.parse_args()
    stamp = datetime.now().strftime('%Y%m%d')
    if a.kind == 'reviews':
        rows = reviews(a.lang, a.days)
        path = os.path.join(ROOT, 'data', 'raw', 'reviews', f'steam_global_{a.lang}_{stamp}.csv')
        write(path, REVIEW_FIELDS, rows)
        log(f'steam_reviews_{a.lang}', 'steam_official_api', len(rows), a.days, 'Steam PC 글로벌판 리뷰. 모바일 스토어 표본 아님')
    else:
        rows = news(a.days)
        path = os.path.join(ROOT, 'data', 'raw', 'updates', f'updates_global_steam_{stamp}.csv')
        write(path, UPDATE_FIELDS, rows)
        log('steam_news', 'steam_official_api', len(rows), a.days, 'Steam 커뮤니티 공지. 모바일 적용일과 다를 수 있음')
    print(path, len(rows))

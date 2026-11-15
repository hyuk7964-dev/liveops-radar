"""정제: data/raw → data/processed/game_reviews.csv · game_updates.csv (DATA_PLAN 3장 규칙).

1. (store, source_review_id) 중복은 하나만 남긴다.
2. 같은 날 같은 본문은 지우지 않고 possible_duplicate=True.
3. 본문 5자 미만 · 빈 본문은 분석에서 뺀다(analyzable=False). 행은 남긴다.
4. role (2026-11-08 사용자 결정 D2 수정): 일본어 = 앱스토어 JP main, 한국어 · 영어 = Steam main(PC 글로벌판 한시 승격),
   앱스토어 KR(2023~2026-02 오래된 글) · Gamerch = aux. Apple RSS가 KR 최신 · US 리뷰를 주지 않아서다.
5. 가상 데이터(data/sample)는 읽지 않는다. 원본 파일은 고치지 않는다.

사용: python -m src.preprocess.clean
"""
import csv, glob, os, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.schema import REVIEW_FIELDS, UPDATE_FIELDS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MIN_TEXT = 5
def role(r):
    if r['store'] == 'app_store':
        return 'main' if r['store_country'] == 'JP' else 'aux'
    if r['store'] == 'steam':
        return 'main' if r['language'] in ('ko', 'en') else 'aux'
    return 'main' if r['store'] == 'google_play' else 'aux'


def read(pattern):
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', 'raw', pattern))):
        rows += list(csv.DictReader(open(p, encoding='utf-8-sig')))
    return rows


def main():
    revs, seen, out = read('reviews/*.csv'), set(), []
    dropped_dup = 0
    for r in revs:
        if r.get('is_synthetic') != 'False':
            raise SystemExit(f"raw에 가상 데이터가 있음: {r['review_id']}")
        key = (r['store'], r['source_review_id'] or r['review_id'])
        if key in seen:
            dropped_dup += 1; continue
        seen.add(key)
        r = {c: r.get(c, '') for c in REVIEW_FIELDS}
        r['analyzable'] = str(len(r['review_text'].strip()) >= MIN_TEXT)
        r['role'] = role(r)
        out.append(r)
    same = collections.Counter((r['store'], r['review_date'], r['review_text'].strip()) for r in out)
    for r in out:
        r['possible_duplicate'] = str(same[(r['store'], r['review_date'], r['review_text'].strip())] > 1)
    fields = REVIEW_FIELDS + ['analyzable', 'role', 'possible_duplicate']
    p = os.path.join(ROOT, 'data', 'processed', 'game_reviews.csv')
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    ups = [{c: u.get(c, '') for c in UPDATE_FIELDS} for u in read('updates/*.csv')]
    with open(os.path.join(ROOT, 'data', 'processed', 'game_updates.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=UPDATE_FIELDS); w.writeheader(); w.writerows(ups)
    c = collections.Counter((r['role'], r['store'], r['store_country'] or '-', r['language']) for r in out if r['analyzable'] == 'True')
    print(f'리뷰 {len(revs)} → 중복 제거 {dropped_dup} → {len(out)}행, 분석 가능 {sum(c.values())}, 공지 {len(ups)}')
    for k, v in sorted(c.items()):
        print('  ', k, v)


if __name__ == '__main__':
    main()

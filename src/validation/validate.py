"""CSV 검증 + 데이터 품질 리포트.

사용:
  python -m src.validation.validate                 # data/raw 와 data/sample 전체 검사, docs/data_quality_report.md 작성
  python -m src.validation.validate 파일.csv ...     # 지정 파일만 검사(리포트는 화면에만)

규칙(VALIDATION_PLAN.md 1장): 필수 열 · 필수 값 · 허용 값 · 날짜 형식 · ID 중복 · 실제/가상 폴더 일치.
"""
import csv, glob, os, sys, collections
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.schema import (REVIEW_COLUMNS, UPDATE_COLUMNS, REGIONS, STORES, LANGS, METHODS, UPDATE_TYPES,
                        detect_language)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PILOT_MIN = 100   # 브리프 10장: 언어별 분석 가능한 본문 100건
NOTICE_MIN = 3    # 지역별 주요 공지 3건
MIN_TEXT = 5      # 이 글자 수 미만은 '분석 가능한 본문'에서 뺀다 ("야르" 같은 한 단어)


def is_date(s, fmt):
    try:
        datetime.strptime(s, fmt); return True
    except ValueError:
        return False


def check(path):
    """한 파일을 검사해 (종류, 행 목록, 오류 목록)을 돌려준다."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
        header = rows[0].keys() if rows else csv.DictReader(open(path, encoding='utf-8-sig')).fieldnames or []
    kind = 'reviews' if 'review_id' in header else 'updates' if 'update_id' in header else None
    if kind is None:
        return None, rows, ['review_id 또는 update_id 열이 없음']
    cols = REVIEW_COLUMNS if kind == 'reviews' else UPDATE_COLUMNS
    errs = [f'필수 열 없음: {c}' for c, req in cols if req and c not in header]
    if errs:
        return kind, rows, errs
    for r in rows:  # 선택 열이 없는 옛 파일도 검사할 수 있게 빈 값으로 채운다
        for c, _ in cols:
            r.setdefault(c, '')
    in_sample = os.sep + 'sample' + os.sep in os.path.abspath(path)
    idk = 'review_id' if kind == 'reviews' else 'update_id'
    ids = collections.Counter(r[idk] for r in rows)
    errs += [f'ID 중복: {k} ({v}회)' for k, v in ids.items() if v > 1]
    for i, r in enumerate(rows, 2):  # 2 = 머리글 다음 줄
        e = lambda m: errs.append(f'{i}행: {m}')
        for c, req in cols:
            if req and not r[c].strip():
                e(f'{c} 비어 있음')
        if r['service_region'] and r['service_region'] not in REGIONS: e(f"service_region 허용 값 아님: {r['service_region']}")
        if r['language'] and r['language'] not in LANGS: e(f"language 허용 값 아님: {r['language']}")
        if r['collection_method'] and r['collection_method'] not in METHODS: e(f"collection_method 허용 값 아님: {r['collection_method']}")
        if r['is_synthetic'] not in ('True', 'False'): e('is_synthetic은 True 또는 False')
        if in_sample and r['is_synthetic'] != 'True': e('sample 폴더인데 is_synthetic=False (가상과 실제 혼동)')
        if not in_sample and r['is_synthetic'] == 'True': e('raw 폴더인데 is_synthetic=True (가상과 실제 혼동)')
        if (r['collection_method'] == 'synthetic') != (r['is_synthetic'] == 'True'): e('collection_method와 is_synthetic 불일치')
        if not is_date(r['collected_at'], '%Y-%m-%dT%H:%M:%SZ'): e('collected_at 형식은 YYYY-MM-DDTHH:MM:SSZ')
        if kind == 'reviews':
            if r['store'] not in STORES: e(f"store 허용 값 아님: {r['store']}")
            if not is_date(r['review_date'], '%Y-%m-%d'): e('review_date 형식은 YYYY-MM-DD')
            if r['rating'] and r['rating'] not in {'1', '2', '3', '4', '5'}: e('rating은 1~5 또는 빈 값')
            if r['store'] != 'gamerch' and not r['rating'] and r['recommended'] not in ('True', 'False'): e('rating과 recommended가 둘 다 없음')  # 커뮤니티 글은 별점이 없다
        else:
            if r['update_type'] not in UPDATE_TYPES: e(f"update_type 허용 값 아님: {r['update_type']}")
            for c in ('notice_date', 'update_date'):
                if r[c] and not is_date(r[c], '%Y-%m-%d'): e(f'{c} 형식은 YYYY-MM-DD')
    return kind, rows, errs


def pct(n, d):
    return f'{100 * n / d:.0f}%' if d else '—'


def report(results):
    L = [f'# 데이터 품질 리포트', '', f'생성: {datetime.now():%Y-%m-%d %H:%M} · 도구 `src/validation/validate.py` · 기준 VALIDATION_PLAN.md', '']
    L += ['## 1. 파일별 검사', '', '| 파일 | 종류 | 행 | 실제/가상 | 오류 |', '|---|---|---|---|---|']
    for p, (k, rows, errs) in results.items():
        syn = {r.get('is_synthetic') for r in rows}
        L.append(f"| `{os.path.relpath(p, ROOT)}` | {k} | {len(rows)} | {'가상' if syn == {'True'} else '실제' if syn == {'False'} else '혼합'} | {len(errs)} |")
    for p, (k, rows, errs) in results.items():
        if errs:
            L += ['', f'**{os.path.relpath(p, ROOT)} 오류 (처음 20개)**', ''] + [f'- {x}' for x in errs[:20]]
    real = {p: v for p, v in results.items() if os.sep + 'sample' + os.sep not in p}
    revs = [r for k, rows, _ in real.values() if k == 'reviews' for r in rows]
    ups = [r for k, rows, _ in real.values() if k == 'updates' for r in rows]
    L += ['', '## 2. 실제 리뷰 품질 (가상 데이터 제외)', '']
    if not revs:
        L.append('실제 리뷰 없음.')
    else:
        dup_src = sum(v - 1 for v in collections.Counter((r['store'], r['source_review_id']) for r in revs if r['source_review_id']).values())
        dup_txt = sum(v - 1 for v in collections.Counter((r['store'], r['review_date'], r['review_text'].strip()) for r in revs).values())
        usable = [r for r in revs if len(r['review_text'].strip()) >= MIN_TEXT]
        L += [f'- 전체 {len(revs)}건 · 기간 {min(r["review_date"] for r in revs)} ~ {max(r["review_date"] for r in revs)}',
              f'- 중복: 원본 ID 중복 {dup_src}건 / 같은 날 같은 본문 {dup_txt}건 (후자는 제거하지 않고 표시만)',
              f'- 분석 가능한 본문({MIN_TEXT}자 이상): {len(usable)}건 ({pct(len(usable), len(revs))})', '',
              '| 필드 | 확보율 |', '|---|---|']
        for c in ('review_date', 'rating', 'recommended', 'app_version', 'store_country', 'developer_reply', 'review_title', 'playtime_at_review_min'):
            L.append(f"| {c} | {pct(sum(1 for r in revs if r[c].strip()), len(revs))} |")
        L += ['', '**언어 (본문 감지 기준) × 출처 라벨**', '', '| 감지 언어 | 건수 | 분석 가능 | 출처 라벨과 일치 |', '|---|---|---|---|']
        label = {'koreana': 'ko', 'english': 'en', 'japanese': 'ja'}
        for lg in ('ko', 'ja', 'en', 'other', 'unknown'):
            g = [r for r in revs if r['language'] == lg]
            if g:
                same = sum(1 for r in g if label.get(r['source_language_label']) == lg)
                L.append(f"| {lg} | {len(g)} | {sum(1 for r in g if len(r['review_text'].strip()) >= MIN_TEXT)} | {pct(same, len(g))} |")
        L += ['', '**스토어 × 출처 라벨**', '']
        for (s, lb), n in sorted(collections.Counter((r['store'], r['source_language_label'] or '—') for r in revs).items()):
            rec = [r for r in revs if r['store'] == s and (r['source_language_label'] or '—') == lb and r['recommended']]
            L.append(f"- {s} / {lb}: {n}건" + (f" · 추천 비율 {pct(sum(r['recommended'] == 'True' for r in rec), len(rec))}" if rec else ''))
    L += ['', '## 3. 파일럿 통과 기준 (브리프 10장)', '', '| 항목 | 기준 | 현재 | 판정 |', '|---|---|---|---|']
    for lg, name in (('ko', '한국어'), ('ja', '일본어'), ('en', '영어')):
        n = sum(1 for r in revs if r['language'] == lg and len(r['review_text'].strip()) >= MIN_TEXT)
        L.append(f"| {name} 리뷰 | 분석 가능 본문 {PILOT_MIN}건 | {n}건 | {'통과' if n >= PILOT_MIN else '미달'} |")
    # 한국 공지(넥슨 커뮤니티)는 서비스 권역이 GLOBAL이라 공지 언어(ko)로 센다
    for name, f in (('한국(넥슨 커뮤니티)', lambda u: u['language'] == 'ko'), ('일본(공식 뉴스)', lambda u: u['service_region'] == 'JP'),
                    ('글로벌(Steam 공지)', lambda u: u['collection_method'] == 'steam_official_api')):
        n = sum(1 for u in ups if f(u))
        L.append(f"| {name} 업데이트 공지 | {NOTICE_MIN}건 | {n}건 | {'통과' if n >= NOTICE_MIN else '미달'} |")
    has = lambda c: pct(sum(1 for r in revs if r[c].strip()), len(revs)) if revs else '—'
    L.append(f"| 출처와 수집 방법 | 모든 레코드 | source_url {has('source_url')} · method {has('collection_method')} | {'통과' if revs and all(r['source_url'] and r['collection_method'] for r in revs) else '미달'} |")
    core = sum(1 for r in revs if r['review_date'] and (r['rating'] or r['recommended'])) if revs else 0
    L.append(f"| 별점(또는 추천)과 날짜 | 90% 이상 | {pct(core, len(revs))} | {'통과' if revs and core / len(revs) >= 0.9 else '미달'} |")
    L.append(f"| 앱 버전 | 확보율 측정 · 결측 허용 | {has('app_version')} | 측정 완료 |" if revs else '| 앱 버전 | — | — | — |')
    return '\n'.join(L) + '\n'


def main(paths):
    write_doc = not paths
    if not paths:
        paths = sorted(glob.glob(os.path.join(ROOT, 'data', 'raw', '*', '*.csv')) + glob.glob(os.path.join(ROOT, 'data', 'sample', '*.csv')))
    results = {os.path.abspath(p): check(p) for p in paths}
    md = report(results)
    if write_doc:
        open(os.path.join(ROOT, 'docs', 'data_quality_report.md'), 'w', encoding='utf-8').write(md)
    print(md)
    return 1 if any(errs for _, _, errs in results.values()) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

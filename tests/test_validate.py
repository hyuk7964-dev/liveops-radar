"""검증 도구 자체 테스트. 실행: python tests/test_validate.py (pytest 없이 돈다)"""
import csv, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.schema import REVIEW_FIELDS, detect_language
from src.validation.validate import check

ROOT = os.path.join(os.path.dirname(__file__), '..')


def row(**kw):
    r = dict.fromkeys(REVIEW_FIELDS, '')
    r.update(review_id='syn_1', game_id='blue_archive', service_region='GLOBAL', store='steam', language='ko',
             review_date='2026-11-01', collected_at='2026-11-08T00:00:00Z', recommended='True',
             review_text='[가상] 테스트 리뷰입니다', source_url='synthetic://test', collection_method='synthetic',
             data_permission_note='가상 데이터', is_synthetic='True')
    r.update(kw)
    return r


def write(folder, rows):
    d = os.path.join(tempfile.mkdtemp(), folder); os.makedirs(d)
    p = os.path.join(d, 't.csv')
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_FIELDS); w.writeheader(); w.writerows(rows)
    return p


def errs(folder, rows):
    return check(write(folder, rows))[2]


# 언어 감지
assert detect_language('야르') == 'ko'
assert detect_language('Great game but gacha rates are bad') == 'en'
assert detect_language('ガチャが渋い') == 'ja'
assert detect_language('😭😭') == 'unknown'
assert detect_language('好玩') == 'other'

# 정상 가상 행은 sample 폴더에서 통과
assert errs('sample', [row()]) == []
# 가상 데이터가 raw 폴더에 섞이면 잡는다
assert any('혼동' in e for e in errs('raw', [row()]))
# 실제 데이터인데 sample 폴더에 있으면 잡는다
assert any('혼동' in e for e in errs('sample', [row(is_synthetic='False', collection_method='steam_official_api')]))
# 필수 값 · 허용 값 · 날짜 · ID 중복 · 별점 범위
assert any('review_text 비어' in e for e in errs('sample', [row(review_text='')]))
assert any('service_region' in e for e in errs('sample', [row(service_region='US')]))
assert any('review_date 형식' in e for e in errs('sample', [row(review_date='2026/11/01')]))
assert any('ID 중복' in e for e in errs('sample', [row(), row()]))
assert any('rating은' in e for e in errs('sample', [row(rating='6')]))
assert any('둘 다 없음' in e for e in errs('sample', [row(recommended='')]))

# 저장소의 가상 샘플 파일은 오류가 없어야 한다
sample = os.path.join(ROOT, 'data', 'sample', 'synthetic_reviews.csv')
assert check(sample)[2] == [], check(sample)[2]
print('ok: 16 checks')

# 웹사이트 점검: python -X utf8 -m pytest tests/test_app.py  (또는 python -X utf8 tests/test_app.py)
import os, sys
import pandas as pd
from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(__file__), '..', 'app.py')


def test_app_runs_without_error():
    # 사이드바 버튼(radio) 7개 섹션을 하나씩 눌러 모두 오류 없이 그려지는지
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    nav = at.sidebar.radio[0]
    assert list(nav.options) == ['개요', '언어별 불만 지도', '이슈 탐색', '공지와 반응', '다음 과제', 'AI 정확도', '커뮤니티 온도']
    for s in nav.options:
        at.sidebar.radio[0].set_value(s).run()
        assert not at.exception, (s, at.exception)


def test_display_rules():
    sys.path.insert(0, os.path.dirname(APP))
    import app
    # 11/12 결정(일본 운영 P1 → P2)이 AI 초안 화면에 반영되고, 영어 주제 키가 한국어로 바뀐다
    d = app.draft()
    assert app.JA_OPS_P1 in app.md('business_report_draft.md') and app.JA_OPS_P1 not in d and '### 이벤트 운영, ' in d and '### monetization' not in d
    # docs 원문 전문 칸은 화면에서만 가운데 점과 줄표를 쉼표로 (docs 파일은 그대로)
    assert '·' not in d and '—' not in d and '·' in app.md('business_report_draft.md')
    assert app.plain('가챠 구조 · 가격, 난이도·단조로움 — 끝') == '가챠 구조, 가격, 난이도, 단조로움, 끝'
    # 정확도는 리포트에서 읽어 덱과 같은 값
    acc, bands, mon, overall = app.eval_report()
    assert {l: v['acc'] for l, v in acc.items()} == {'ko': 0.76, 'ja': 0.82, 'en': 0.68} and round(overall, 2) == 0.75
    assert mon == {'ko': 1.0, 'ja': 0.70, 'en': 0.68}
    # 리뷰 발췌의 markdown 특수문자는 이스케이프
    assert app.esc('*굵게* $5 [링크](x)') == r'\*굵게\* \$5 \[링크\]\(x\)'


def test_temperature_formula():
    sys.path.insert(0, os.path.dirname(APP))
    import app  # streamlit 밖에서 import하면 화면 코드는 경고만 내고 지나간다
    # 2026-11-11(수)은 11-10(화) 주. 긍정 7 · 부정 2 · 기타 1 → 70 + 5 − 10 = 65도
    notes = pd.DataFrame({'post_date': ['2026-11-11'] * 10, 'stance': ['옹호'] * 7 + ['반발'] * 2 + ['중립']})
    t = app.temperature(notes)
    assert str(t.iloc[0, 0]) == '2026-11-10' and t['온도'][0] == 65.0 and t['n'][0] == 10


def test_public_data_excerpt_only():
    # 배포본은 data/public 발췌만 읽는다: 원문 열 없음 · 발췌 200자 이내 · 숫자가 덱과 같음(671 · 65 · 149)
    sys.path.insert(0, os.path.join(os.path.dirname(APP)))
    from src.reporting.public_data import build, P
    assert build() == {'reviews': 671, 'updates': 65, 'gold': 149}
    r = pd.read_csv(P('public', 'reviews.csv'), encoding='utf-8-sig', keep_default_na=False)
    assert 'review_text' not in r.columns and r.excerpt.str.len().max() <= 200
    app_src = open(APP, encoding='utf-8').read()
    assert 'game_reviews' not in app_src and 'gold_labels' not in app_src


if __name__ == '__main__':
    test_app_runs_without_error(); test_display_rules(); test_temperature_formula(); test_public_data_excerpt_only(); print('ok')

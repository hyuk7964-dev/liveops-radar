# 웹사이트 점검: python -X utf8 -m pytest tests/test_app.py  (또는 python -X utf8 tests/test_app.py)
import os, sys
import pandas as pd
from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(__file__), '..', 'app.py')


def test_app_runs_without_error():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 7


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
    test_app_runs_without_error(); test_temperature_formula(); test_public_data_excerpt_only(); print('ok')

"""자체 정의 정량 지표 2개 (1108 멘토 피드백) → data/processed/weighted_metrics.csv + docs/weighted_metrics.md

1. 공감 가중 부정 언급률: 리뷰 하나를 1이 아니라 w = 1 + ln(1 + votes_up)로 센다.
   로그로 눌러서 공감 수백 개짜리 리뷰 한 건이 전체를 덮지 않게 한다.
   가중률 / 단순률 = 공감 배율. 1보다 크면 "다른 유저도 동의하는 불만".
2. 장기 이용자 비중: 해당 주제 부정 언급 중 플레이 시간이 그 언어 표본 중앙값 이상인 리뷰 비율.
   기준이 중앙값이라 50%가 중립. 높으면 오래 한 유저가 더 불만. Steam만(앱스토어는 플레이 시간 없음).

n < 30이면 결론 유보 표시(VALIDATION_PLAN 3장). 메인 데이터(role=main)만 쓴다.
사용: python -X utf8 -m src.analysis.weighted_metrics   /  자체 점검: ... --test
"""
import csv, math, os, statistics, sys, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
P = lambda *a: os.path.join(ROOT, *a)
MIN_N = 30


def weight(votes):
    return 1 + math.log1p(max(0, int(float(votes or 0))))


def compute(reviews, topics):
    """reviews: {id: row}, topics: rows of review_topics → 지표 행 목록"""
    out = []
    for lg in sorted({r['language'] for r in reviews.values()}):
        ids = [k for k, r in reviews.items() if r['language'] == lg]
        W = {k: weight(reviews[k]['votes_up']) for k in ids}
        pt = {k: float(reviews[k]['playtime_at_review_min']) for k in ids if reviews[k]['playtime_at_review_min'].strip()}
        med = statistics.median(pt.values()) if pt else None
        neg = collections.defaultdict(set)  # 리뷰당 주제 1번만 센다
        for t in topics:
            if t['review_id'] in W and t['sentiment'] == 'negative' and t['topic'] != 'other':
                neg[t['topic']].add(t['review_id'])
        for topic, rs in sorted(neg.items(), key=lambda x: -len(x[1])):
            plain = len(rs) / len(ids) * 100
            wrate = sum(W[k] for k in rs) / sum(W.values()) * 100
            withpt = [k for k in rs if k in pt]
            long_share = sum(pt[k] >= med for k in withpt) / len(withpt) * 100 if withpt else None
            out.append({'language': lg, 'topic': topic, 'n_reviews': len(ids), 'n_negative': len(rs),
                        'plain_rate': round(plain, 1), 'weighted_rate': round(wrate, 1), 'vote_lift': round(wrate / plain, 2),
                        'playtime_median_h': round(med / 60, 1) if med else '', 'long_player_share': round(long_share, 1) if long_share is not None else '',
                        'reserved': 'True' if len(rs) < MIN_N else 'False'})
    return out


def test():
    R = {f'r{i}': {'language': 'en', 'votes_up': str(v), 'playtime_at_review_min': str(p)}
         for i, (v, p) in enumerate([(0, 100), (0, 200), (100, 300), (0, 400)])}
    T = [{'review_id': 'r2', 'topic': 'monetization', 'sentiment': 'negative'},
         {'review_id': 'r2', 'topic': 'monetization', 'sentiment': 'negative'},  # 같은 리뷰 중복 → 1번
         {'review_id': 'r0', 'topic': 'ui_ux', 'sentiment': 'negative'},
         {'review_id': 'r1', 'topic': 'other', 'sentiment': 'negative'},
         {'review_id': 'r3', 'topic': 'ui_ux', 'sentiment': 'positive'}]
    m = {x['topic']: x for x in compute(R, T)}
    assert set(m) == {'monetization', 'ui_ux'}
    assert m['monetization']['n_negative'] == 1 and m['monetization']['plain_rate'] == 25.0
    assert m['monetization']['vote_lift'] > 1 > m['ui_ux']['vote_lift']   # 공감 많은 불만이 위로
    assert m['monetization']['long_player_share'] == 100.0 and m['ui_ux']['long_player_share'] == 0.0  # 중앙값 250분
    assert m['ui_ux']['reserved'] == 'True'
    assert weight('') == 1 and weight('0') == 1
    print('test ok')


def main():
    R = {r['review_id']: r for r in csv.DictReader(open(P('data', 'processed', 'game_reviews.csv'), encoding='utf-8-sig'))
         if r['role'] == 'main' and r['analyzable'] == 'True' and r['language'] in ('ko', 'ja', 'en')}
    T = list(csv.DictReader(open(P('data', 'processed', 'review_topics.csv'), encoding='utf-8-sig')))
    rows = compute(R, T)
    with open(P('data', 'processed', 'weighted_metrics.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    L = ['# 자체 정의 정량 지표', '', '> **정확도 측정 완료(2026-11-12, 정답 149건, `docs/ai_evaluation_report.md`).** 감성 Accuracy ko 0.76 · ja 0.82 · en 0.68. monetization 주제 Precision은 ja 0.70 · en 0.68 · ko 1.00(2차 검수 v2, 좁은 규칙: 가챠 구조 · 가격을 직접 평가할 때만). AI가 과금 언급을 사람보다 넉넉하게 세므로 과금 수치는 상한으로 읽는다. 원인 · 제안은 AI 가설이다.', '',
         '- 공감 가중 부정 언급률: 리뷰 가중치 w = 1 + ln(1 + 공감 수). 공감 배율 = 가중률 ÷ 단순률 (1 초과 = 다른 유저도 동의하는 불만)',
         '- 장기 이용자 비중: 부정 언급 중 플레이 시간이 언어 표본 중앙값 이상인 비율 (50% = 중립, Steam만)',
         f'- 부정 언급 {MIN_N}건 미만은 결론 유보', '',
         '| 언어 | 주제 | 리뷰 n | 부정 n | 단순률 | 공감 가중률 | 공감 배율 | 장기 이용자 비중 | 비고 |', '|---|---|---|---|---|---|---|---|---|']
    for x in rows:
        lp = f"{x['long_player_share']}% (중앙값 {x['playtime_median_h']}h)" if x['long_player_share'] != '' else '-'
        L.append(f"| {x['language']} | {x['topic']} | {x['n_reviews']} | {x['n_negative']} | {x['plain_rate']} | {x['weighted_rate']} | {x['vote_lift']} | {lp} | {'결론 유보' if x['reserved'] == 'True' else ''} |")
    open(P('docs', 'weighted_metrics.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'saved {len(rows)} rows → data/processed/weighted_metrics.csv, docs/weighted_metrics.md')


if __name__ == '__main__':
    test() if '--test' in sys.argv else main()

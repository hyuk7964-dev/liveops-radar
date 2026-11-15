"""업데이트 전후 비교 (브리프 8.2). 날짜 기준 연관 관찰이며 인과를 단정하지 않는다.

- 구간: 기준일(적용일, 없으면 공지일) 앞 7일 / 뒤 7일. 한쪽이 MIN_N 미만이면 14일로 넓히고, 그래도 미만이면 '결론 유보'.
- 업데이트와 리뷰 흐름 짝: STREAMS (지역이 맞는 리뷰만 본다)
- 주제 상태: 신규(전 0 · 후 3건 이상) / 지속(전후 모두 3건 이상) / 개선 관찰(전 3건 이상, 100건당 부정 언급이 절반 이하로)
- 같은 구간의 다른 공지는 교란 요인으로 함께 적는다.

사용: python -m src.analysis.update_impact → data/processed/update_impact.json, docs/update_impact_report.md
"""
import csv, json, os, collections
from datetime import date, timedelta
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
P = lambda *a: os.path.join(ROOT, *a)
MIN_N, MIN_TOPIC = 30, 3
# 공지 묶음 → 리뷰 흐름. 모바일 공지와 Steam 리뷰는 같은 글로벌 서비스지만 플랫폼이 달라 따로 표시한다.
STREAMS = {
    'JP 공지 × 앱스토어 JP': (lambda u: u['service_region'] == 'JP', lambda r: r['store'] == 'app_store' and r['store_country'] == 'JP'),
    'KR 공지 × Steam 한국어(PC 표본)': (lambda u: u['language'] == 'ko', lambda r: r['store'] == 'steam' and r['language'] == 'ko'),
    'KR 공지 × Steam 영어(PC 표본)': (lambda u: u['language'] == 'ko', lambda r: r['store'] == 'steam' and r['language'] == 'en'),
}


def d(s):
    return date.fromisoformat(s)


def neg(r):
    return (r['rating'] and int(r['rating']) <= 2) or r['recommended'] == 'False'


def side(R, topics):
    n = len(R)
    c, cn = collections.Counter(), collections.Counter()
    for r in R:
        for t in topics.get(r['review_id'], []):
            c[t['topic']] += 1
            cn[t['topic']] += t['sentiment'] == 'negative'
    rated = [int(r['rating']) for r in R if r['rating']]
    return {'n': n, 'neg_ratio': round(sum(map(neg, R)) / n, 3) if n else None,
            'avg_rating': round(sum(rated) / len(rated), 2) if rated else None,
            'topics': dict(c), 'topic_neg': dict(cn)}


def main():
    revs = [r for r in csv.DictReader(open(P('data', 'processed', 'game_reviews.csv'), encoding='utf-8-sig')) if r['analyzable'] == 'True']
    ups = list(csv.DictReader(open(P('data', 'processed', 'game_updates.csv'), encoding='utf-8-sig')))
    topics = collections.defaultdict(list)
    tp = P('data', 'processed', 'review_topics.csv')
    if os.path.exists(tp):
        for t in csv.DictReader(open(tp, encoding='utf-8-sig')):
            topics[t['review_id']].append(t)
    out, L = [], ['# 업데이트 전후 비교 (날짜 기준 연관 관찰)', '',
                  '업데이트가 리뷰 변화의 원인이라고 단정하지 않는다. 표본이 부족하면 결론을 유보한다.', '']
    for name, (uf, rf) in STREAMS.items():
        R = [r for r in revs if rf(r)]
        U = sorted([u for u in ups if uf(u) and u['update_type'] in ('content', 'character', 'event', 'system', 'balance', 'monetization', 'developer_note')],
                   key=lambda u: u['update_date'] or u['notice_date'])
        L += [f'## {name}', '', f'리뷰 {len(R)}건 · 기간 {min((r["review_date"] for r in R), default="—")} ~ {max((r["review_date"] for r in R), default="—")}', '']
        events = collections.OrderedDict()  # 같은 날 공지는 한 사건으로 묶는다
        for u in U:
            events.setdefault(u['update_date'] or u['notice_date'], []).append(u)
        for day, us in events.items():
            u = dict(us[0], update_title=' + '.join(x['update_title'] for x in us), update_id=' + '.join(x['update_id'] for x in us))
            base = d(day)
            for w in (7, 14):
                pre = [r for r in R if base - timedelta(w) <= d(r['review_date']) < base]
                post = [r for r in R if base < d(r['review_date']) <= base + timedelta(w)]
                if len(pre) >= MIN_N and len(post) >= MIN_N:
                    break
            a, b = side(pre, topics), side(post, topics)
            enough = a['n'] >= MIN_N and b['n'] >= MIN_N
            status = {}
            for k in set(a['topics']) | set(b['topics']):
                x, y = a['topics'].get(k, 0), b['topics'].get(k, 0)
                xn, yn = a['topic_neg'].get(k, 0) / max(a['n'], 1) * 100, b['topic_neg'].get(k, 0) / max(b['n'], 1) * 100
                if x == 0 and y >= MIN_TOPIC: status[k] = 'new'
                elif x >= MIN_TOPIC and y >= MIN_TOPIC: status[k] = 'improved' if yn <= xn / 2 and xn > 0 else 'persistent'
                elif x >= MIN_TOPIC and yn <= xn / 2 and xn > 0: status[k] = 'improved'
            conf = [v['update_title'] for v in ups if v['update_id'] not in u['update_id'] and uf(v)
                    and abs((d(v['update_date'] or v['notice_date']) - base).days) <= w]
            rec = {'stream': name, 'update_id': u['update_id'], 'title': u['update_title'], 'base_date': str(base),
                   'base_is_notice_date': not u['update_date'], 'window_days': w, 'pre': a, 'post': b,
                   'enough_sample': enough, 'topic_status': status, 'confounders': conf, 'source_url': u['source_url']}
            out.append(rec)
            L += [f"### {base} {u['update_title']}", '',
                  f"- 구간 ±{w}일 ({'공지일' if not u['update_date'] else '적용일'} 기준) · 전 n={a['n']} / 후 n={b['n']}" + ('' if enough else ' → **결론 유보(표본 부족)**'),
                  f"- 부정 비율 {a['neg_ratio']} → {b['neg_ratio']}" + (f" · 평균 별점 {a['avg_rating']} → {b['avg_rating']}" if a['avg_rating'] or b['avg_rating'] else ''),
                  f"- 주제 상태(관찰): " + (', '.join(f'{k}={v}' for k, v in sorted(status.items())) or '없음'),
                  f"- 같은 구간 다른 공지(교란 요인): " + ('; '.join(conf[:6]) or '없음'), '']
    json.dump(out, open(P('data', 'processed', 'update_impact.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(P('docs', 'update_impact_report.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()

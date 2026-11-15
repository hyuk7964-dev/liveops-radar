# 웹사이트 배포용 공개 데이터 만들기. 원문 리뷰 CSV 대신 200자 이내 발췌 + 링크만 담는다.
# 실행: python -X utf8 -m src.reporting.public_data   →  data/public/ (reviews.csv · topics.csv · summary.json)
# 원문(data/raw · processed/game_reviews.csv · gold_*.csv)은 배포본에 넣지 않는다 (README 배포 절차)
import json, os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, 'data', *a)
OUT = P('public')
LANGS = ['ko', 'ja', 'en']
MAX = 200


def excerpt(s, n=MAX):
    s = ' '.join(str(s).split())
    return s if len(s) <= n else s[:n - 1] + '…'


def csv(*a):
    return pd.read_csv(P(*a), encoding='utf-8-sig', dtype=str, keep_default_na=False)


def build():
    r = csv('processed', 'game_reviews.csv')
    r = r[(r.role == 'main') & (r.analyzable == 'True') & r.language.isin(LANGS)].copy()
    a = csv('processed', 'review_analysis.csv')[['review_id', 'sentiment', 'issue_summary']]
    r = r.merge(a, on='review_id', how='left')
    r['excerpt'] = r.review_text.map(excerpt)
    reviews = r[['review_id', 'language', 'review_date', 'collection_method', 'votes_up', 'source_url',
                 'excerpt', 'sentiment', 'issue_summary', 'is_synthetic']]
    t = csv('processed', 'review_topics.csv')[['review_id', 'topic', 'sub_topic', 'sentiment']]
    g = csv('processed', 'issue_groups.csv')[['language', 'topic', 'sub_topic', 'issue_group']]
    topics = t.merge(r[['review_id', 'language', 'review_date']], on='review_id').merge(g, on=['language', 'topic', 'sub_topic'], how='left')
    gold = csv('processed', 'gold_labels.csv')
    updates = sum(len(csv('raw', 'updates', f)) for f in os.listdir(P('raw', 'updates')) if f.endswith('.csv'))
    summary = {'reviews': len(reviews), 'updates': updates, 'gold': int((gold.gold_sentiment != '').sum())}
    os.makedirs(OUT, exist_ok=True)
    reviews.to_csv(os.path.join(OUT, 'reviews.csv'), index=False, encoding='utf-8-sig')
    topics.to_csv(os.path.join(OUT, 'topics.csv'), index=False, encoding='utf-8-sig')
    json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    assert reviews.excerpt.str.len().max() <= MAX
    return summary


if __name__ == '__main__':
    print(build())

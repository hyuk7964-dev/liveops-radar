"""2차 묶기: 리뷰마다 자유롭게 붙은 sub_topic을 (언어, 주제)별 대표 이슈 6개 이내로 묶는다.

예) '신규 가챠 불만' '가챠 개편 반발' '새 가챠 시스템 비난' → '가챠 시스템 개편 반발'
결과: data/processed/issue_groups.csv (language, topic, sub_topic, issue_group, model_name)
같은 (언어, 주제)는 이미 묶었으면 다시 부르지 않는다(삭제 후 재실행하면 새로 묶음).

사용: python -m src.analysis.cluster_issues
"""
import csv, json, os, subprocess, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
P = lambda *a: os.path.join(ROOT, *a)
MIN_ROWS = 5
PROMPT = """아래는 블루 아카이브 리뷰에서 AI가 붙인 세부 이슈 이름과 개수다(언어 {lg}, 주제 {topic}).
같은 문제를 가리키는 이름을 묶어 대표 이슈 6개 이내로 정리해라. 대표 이슈 이름은 운영 회의 안건으로 쓸 수 있는 한국어 15자 이내 명사구.
모든 이름을 하나에 넣고, 어디에도 안 맞으면 "기타". JSON 객체만 출력: {{"세부 이슈 이름": "대표 이슈", ...}}

{items}"""


def main():
    R = {r['review_id']: r for r in csv.DictReader(open(P('data', 'processed', 'game_reviews.csv'), encoding='utf-8-sig'))}
    T = [t for t in csv.DictReader(open(P('data', 'processed', 'review_topics.csv'), encoding='utf-8-sig')) if t['review_id'] in R]
    out_p = P('data', 'processed', 'issue_groups.csv')
    done = {(g['language'], g['topic'], g['sub_topic']): g for g in csv.DictReader(open(out_p, encoding='utf-8-sig'))} if os.path.exists(out_p) else {}
    groups = collections.defaultdict(collections.Counter)
    for t in T:
        groups[(R[t['review_id']]['language'], t['topic'])][t['sub_topic']] += 1
    for (lg, topic), c in sorted(groups.items()):
        if sum(c.values()) < MIN_ROWS or lg not in ('ko', 'ja', 'en') or all((lg, topic, s) in done for s in c):
            continue
        r = subprocess.run(['claude', '-p', '--model', 'sonnet', '--output-format', 'json'],
                           input=PROMPT.format(lg=lg, topic=topic, items='\n'.join(f'{s}\t{n}' for s, n in c.most_common())),
                           capture_output=True, text=True, encoding='utf-8', timeout=900)
        meta = json.loads(r.stdout); txt = meta.get('result', '')
        m, _ = json.JSONDecoder().raw_decode(txt[txt.find('{'):])  # 뒤에 붙은 설명 글은 무시
        model = next(iter(meta.get('modelUsage') or {}), 'claude-sonnet (claude -p)')
        for s in c:
            done[(lg, topic, s)] = {'language': lg, 'topic': topic, 'sub_topic': s, 'issue_group': m.get(s, '기타'), 'model_name': model}
        print(lg, topic, sum(c.values()), '→', len(set(m.values())), '개 대표 이슈', flush=True)
        save(out_p, done)  # 그룹마다 저장해 중간에 실패해도 이어서 돈다
    save(out_p, done)


def save(out_p, done):
    with open(out_p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['language', 'topic', 'sub_topic', 'issue_group', 'model_name']); w.writeheader(); w.writerows(done.values())


if __name__ == '__main__':
    main()

"""AI 리뷰 분석: 감성 · 주제(다중) · 근거 발췌 · 요약 · 신뢰도.

- 실행: Claude Code 헤드리스(claude -p, Max 구독). 2026-11-08 사용자 결정. 배포용 Anthropic API는 3주차에 따로.
- 결과는 data/processed/analysis.sqlite에 캐시(review_id + PROMPT_VERSION). 다시 돌려도 이미 분석한 리뷰는 부르지 않는다.
- 근거 발췌가 원문에 실제로 있는지 코드로 확인한다(evidence_in_text). 없으면 AI가 지어낸 근거로 본다.
- ai_confidence는 모델이 낸 값이며 정확도가 아니다. 정확도는 사람 정답(gold_labels.csv)으로 따로 잰다.

사용: python -m src.analysis.classify [--role main|aux|all] [--limit N]
"""
import argparse, csv, json, os, re, sqlite3, subprocess, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PROMPT_VERSION = 'v1-2026-11-08'
BATCH = 40
CATS = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'reference', 'category_dictionary.csv'), encoding='utf-8-sig')))
CAT_KEYS = [c['topic'] for c in CATS]

PROMPT = """너는 모바일 수집형 RPG(블루 아카이브) 라이브옵스 분석가다. 아래 리뷰들은 한국어 · 일본어 · 영어가 섞여 있다.
각 리뷰를 원문 언어 그대로 이해해서 분석해라. 반어 · 밈 · 은어 · 오탈자에 주의하고, 애매하면 topic을 other로 두고 confidence를 낮춰라.

주제(topic, 리뷰 하나에 여러 개 가능):
{cats}

출력 규칙:
- sentiment: positive / neutral / negative / mixed (리뷰 전체)
- topics: [{{"topic": 위 키 중 하나, "sub_topic": 한국어 15자 이내 구체 이슈, "sentiment": positive/neutral/negative, "evidence": 원문에서 그대로 복사한 20~80자 구절, "confidence": 0~1}}]
- evidence는 반드시 원문 그대로 복사한다. 번역하거나 고쳐 쓰지 않는다.
- summary: 한국어 40자 이내 요약. 원문에 없는 내용을 더하지 않는다.
- confidence: 리뷰 전체 판단의 확신 0~1
JSON 배열만 출력: [{{"id": "...", "sentiment": "...", "topics": [...], "summary": "...", "confidence": 0.0}}]

리뷰:
{reviews}"""


def db():
    con = sqlite3.connect(os.path.join(ROOT, 'data', 'processed', 'analysis.sqlite'))
    con.execute('create table if not exists analysis (review_id text, prompt_version text, model_name text, analyzed_at text, result text, primary key (review_id, prompt_version))')
    return con


def call_claude(prompt):
    r = subprocess.run(['claude', '-p', '--model', 'sonnet', '--output-format', 'json'], input=prompt,
                       capture_output=True, text=True, encoding='utf-8', timeout=1200)
    meta = json.loads(r.stdout)
    text = meta.get('result', '')
    models = list((meta.get('modelUsage') or {}).keys())
    return json.loads(text[text.find('['):text.rfind(']') + 1]), (models[0] if models else 'claude-sonnet (claude -p)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--role', default='all'); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    revs = [r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'processed', 'game_reviews.csv'), encoding='utf-8-sig'))
            if r['analyzable'] == 'True' and (a.role == 'all' or r['role'] == a.role)]
    if a.limit: revs = revs[:a.limit]
    con = db()
    done = {k for (k,) in con.execute('select review_id from analysis where prompt_version=?', (PROMPT_VERSION,))}
    todo = [r for r in revs if r['review_id'] not in done]
    cats = '\n'.join(f"- {c['topic']}: {c['definition']} (예: {c['negative_examples']})" for c in CATS)
    print(f'대상 {len(revs)} · 캐시 {len(revs) - len(todo)} · 새로 분석 {len(todo)}', flush=True)
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        lines = '\n'.join(f"[{r['review_id']}] " + (r['review_title'] + ' / ' if r['review_title'] else '') + r['review_text'].replace('\n', ' ')[:700] for r in batch)
        for attempt in range(2):
            try:
                res, model = call_claude(PROMPT.format(cats=cats, reviews=lines)); break
            except Exception as e:
                print('retry', i, e, flush=True); res, model = [], ''
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        con.executemany('insert or replace into analysis values (?,?,?,?,?)',
                        [(x['id'], PROMPT_VERSION, model, ts, json.dumps(x, ensure_ascii=False)) for x in res if 'id' in x])
        con.commit()
        print(f'{i + len(batch)}/{len(todo)} model={model}', flush=True)
    export(con, {r['review_id']: r for r in revs})


def norm(s):
    # 공백 · 줄바꿈 · 제목과 본문을 잇는 ' / '는 비교에서 뺀다(같은 글자인데 형식만 다른 경우 오판 방지)
    return re.sub(r'[\s/]+', '', s)


def export(con, revs):
    """SQLite 캐시 → review_analysis.csv · review_topics.csv (브리프 6.4 · 6.5)"""
    A, T = [], []
    for rid, pv, model, ts, res in con.execute('select * from analysis where prompt_version=?', (PROMPT_VERSION,)):
        if rid not in revs:
            continue
        x, text = json.loads(res), revs[rid]['review_title'] + ' ' + revs[rid]['review_text']
        A.append({'review_id': rid, 'sentiment': x.get('sentiment', ''), 'issue_summary': x.get('summary', ''),
                  'ai_confidence': x.get('confidence', ''), 'model_name': model, 'prompt_version': pv,
                  'analyzed_at': ts, 'reviewed_by_human': 'False'})
        for t in x.get('topics', []):
            ev = t.get('evidence', '')
            T.append({'review_id': rid, 'topic': t.get('topic') if t.get('topic') in CAT_KEYS else 'other',
                      'sub_topic': t.get('sub_topic', ''), 'sentiment': t.get('sentiment', ''), 'evidence': ev,
                      'evidence_in_text': str(bool(ev) and norm(ev) in norm(text)), 'confidence': t.get('confidence', '')})
    for name, rows in (('review_analysis.csv', A), ('review_topics.csv', T)):
        if rows:
            with open(os.path.join(ROOT, 'data', 'processed', name), 'w', encoding='utf-8-sig', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    bad = sum(1 for t in T if t['evidence_in_text'] == 'False')
    print(f'분석 {len(A)}건 · 주제 {len(T)}행 · 원문에 없는 근거 {bad}건')


if __name__ == '__main__':
    main()

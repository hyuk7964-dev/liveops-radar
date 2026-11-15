"""AI 품질 평가: 사람 정답(gold_labels.csv) vs AI 결과 → docs/ai_evaluation_report.md (VALIDATION_PLAN 2장).

- gold_sentiment: positive / neutral / negative / mixed
- gold_topics: 주제 키를 ; 로 구분 (예: monetization;event_ops)
- 정답이 비어 있는 행은 건너뛴다. 언어별로 따로 잰다.

사용: python -m src.validation.evaluate
"""
import csv, os, collections
from datetime import datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
P = lambda *a: os.path.join(ROOT, *a)
SENTS = ['positive', 'neutral', 'negative', 'mixed']


def f1(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    gold = [g for g in csv.DictReader(open(P('data', 'processed', 'gold_labels.csv'), encoding='utf-8-sig')) if g['gold_sentiment'].strip()]
    ai = {a['review_id']: a for a in csv.DictReader(open(P('data', 'processed', 'review_analysis.csv'), encoding='utf-8-sig'))}
    tops = collections.defaultdict(set)
    for t in csv.DictReader(open(P('data', 'processed', 'review_topics.csv'), encoding='utf-8-sig')):
        tops[t['review_id']].add(t['topic'])
    L = ['# AI 분류 품질 평가', '', f'생성 {datetime.now():%Y-%m-%d %H:%M} · 정답 {len(gold)}건 · 도구 `src/validation/evaluate.py`', '']
    if not gold:
        L.append('사람 정답이 아직 없다. `data/processed/gold_labels.csv`의 gold_sentiment · gold_topics를 채운 뒤 다시 실행.')
    for lg in ('ko', 'ja', 'en'):
        G = [g for g in gold if g['language'] == lg and g['review_id'] in ai]
        if not G:
            continue
        acc = sum(ai[g['review_id']]['sentiment'] == g['gold_sentiment'] for g in G) / len(G)
        fs = []
        for s in SENTS:
            tp = sum(ai[g['review_id']]['sentiment'] == s and g['gold_sentiment'] == s for g in G)
            fp = sum(ai[g['review_id']]['sentiment'] == s and g['gold_sentiment'] != s for g in G)
            fn = sum(ai[g['review_id']]['sentiment'] != s and g['gold_sentiment'] == s for g in G)
            if tp + fp + fn: fs.append(f1(tp, fp, fn)[2])
        L += [f'## {lg} (n={len(G)})', '', f'- 감성 Accuracy {acc:.2f} · Macro F1 {sum(fs) / len(fs):.2f}', '',
              '| 주제 | 정답 수 | Precision | Recall | F1 |', '|---|---|---|---|---|']
        keys = sorted({k for g in G for k in g['gold_topics'].split(';') if k} | {k for g in G for k in tops[g['review_id']]})
        for k in keys:
            tp = sum(k in tops[g['review_id']] and k in g['gold_topics'].split(';') for g in G)
            fp = sum(k in tops[g['review_id']] and k not in g['gold_topics'].split(';') for g in G)
            fn = sum(k not in tops[g['review_id']] and k in g['gold_topics'].split(';') for g in G)
            p, r, f = f1(tp, fp, fn)
            L.append(f'| {k} | {tp + fn} | {p:.2f} | {r:.2f} | {f:.2f} |')
        L += ['', '| AI 신뢰도 구간 | n | 감성 정답률 |', '|---|---|---|']
        for lo, hi in ((0, .6), (.6, .8), (.8, 1.01)):
            B = [g for g in G if lo <= float(ai[g['review_id']]['ai_confidence'] or 0) < hi]
            if B:
                L.append(f"| {lo:.1f}~{min(hi, 1):.1f} | {len(B)} | {sum(ai[g['review_id']]['sentiment'] == g['gold_sentiment'] for g in B) / len(B):.2f} |")
        L.append('')
    L += recheck_section(gold, ai, tops)
    open(P('docs', 'ai_evaluation_report.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


def recheck_section(gold, ai, tops):
    """monetization 2차 검수(gold_recheck_monetization.csv, Y/N)를 덮어 쓴 v2를 v1과 나란히. 다 채우기 전엔 진행률만."""
    path = P('data', 'processed', 'gold_recheck_monetization.csv')
    if not os.path.exists(path):
        return []
    R = {r['review_id']: r['monetization_v2'].strip().upper() for r in csv.DictReader(open(path, encoding='utf-8-sig'))}
    done = sum(v in ('Y', 'N') for v in R.values())
    L = ['## monetization 2차 검수 (좁은 규칙: 가챠 구조 자체(확률 · 천장 · 픽업)나 가격을 직접 평가할 때만 monetization)', '',
         f'- 검수 대상 {len(R)}건(본문에 가챠 · 과금 단어가 있는 정답 행, AI 결과와 무관하게 선정) · 완료 {done}건', '']
    if done < len(R):
        return L + ['- 완료 전이라 v2 수치는 아직 내지 않는다.', '']
    L += ['| 언어 | v1 Precision | v1 Recall | v2 Precision | v2 Recall | v2 F1 |', '|---|---|---|---|---|---|']
    for lg in ('ko', 'ja', 'en'):
        G = [g for g in gold if g['language'] == lg and g['review_id'] in ai]
        row = []
        for v2 in (False, True):
            def has(g):
                if v2 and g['review_id'] in R:
                    return R[g['review_id']] == 'Y'
                return 'monetization' in g['gold_topics'].split(';')
            tp = sum('monetization' in tops[g['review_id']] and has(g) for g in G)
            fp = sum('monetization' in tops[g['review_id']] and not has(g) for g in G)
            fn = sum('monetization' not in tops[g['review_id']] and has(g) for g in G)
            row.append(f1(tp, fp, fn))
        L.append(f'| {lg} | {row[0][0]:.2f} | {row[0][1]:.2f} | {row[1][0]:.2f} | {row[1][1]:.2f} | {row[1][2]:.2f} |')
    return L + ['']


if __name__ == '__main__':
    main()

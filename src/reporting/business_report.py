"""AI 사업PM 개선 제안 (브리프 8.4 11칸 형식) → docs/business_report_draft.md

1. 메인 데이터에서 언어별 부정 주제 · 세부 이슈 상위를 코드로 센다(숫자는 AI가 아니라 코드가 만든다).
2. 이슈마다 원문 발췌(200자 이내, 원문 근거 검증 통과분만)와 표본 수를 붙여 claude -p에 넘긴다.
3. AI는 원인 가설 · 확인할 정보 · 개선 방향 · 실행 과제 · 우선순위 제안 · 리스크 · 사후 검증만 쓴다.
   내부 KPI 수치 · 매출 효과 · 인과 단정 금지. 우선순위는 'PM 검토용 제안'.
4. 정확도 측정 전이면 보고서 맨 위에 '정확도 미검증 초안'을 붙인다.

사용: python -m src.reporting.business_report [--top 3]
"""
import argparse, csv, json, os, subprocess, collections
from datetime import datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
P = lambda *a: os.path.join(ROOT, *a)
STREAM = {'ko': 'Steam 한국어 (PC 글로벌판 표본)', 'ja': '앱스토어 JP', 'en': 'Steam 영어 (PC 글로벌판 표본)'}

PROMPT = """너는 게임회사 사업PM이다. 블루 아카이브 공개 리뷰 분석에서 나온 이슈 하나에 대해 개선 제안서를 쓴다.
규칙:
- 아래 '데이터'에 있는 숫자와 원문만 근거로 쓴다. 새 숫자를 만들지 않는다.
- 매출 · DAU · 리텐션 · 결제전환 같은 내부 KPI를 추정하거나 수치로 쓰지 않는다.
- 원인은 '가설'로만 쓴다. 업데이트가 원인이라고 단정하지 않는다.
- 우선순위는 P0~P3 중 하나를 'PM 검토용 제안'으로 쓰고 이유를 한 줄로.
- 한국어로, 칸마다 1~3줄.
JSON 객체만 출력:
{{"observed_problem": "", "cause_hypotheses": ["", ""], "info_needed": ["", ""], "direction": "", "action_items": ["", ""], "priority": "P1", "priority_reason": "", "expected_effect_qualitative": "", "risks": [""], "followup_check": ""}}

데이터:
{data}"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--top', type=int, default=3); a = ap.parse_args()
    R = {r['review_id']: r for r in csv.DictReader(open(P('data', 'processed', 'game_reviews.csv'), encoding='utf-8-sig')) if r['role'] == 'main' and r['analyzable'] == 'True'}
    T = [t for t in csv.DictReader(open(P('data', 'processed', 'review_topics.csv'), encoding='utf-8-sig')) if t['review_id'] in R]
    G = {(g['language'], g['topic'], g['sub_topic']): g['issue_group'] for g in csv.DictReader(open(P('data', 'processed', 'issue_groups.csv'), encoding='utf-8-sig'))}  # 2차 묶기 결과
    gold_done = os.path.exists(P('docs', 'ai_evaluation_report.md')) and '감성 Accuracy' in open(P('docs', 'ai_evaluation_report.md'), encoding='utf-8').read()
    L = ['# AI 사업PM 개선 제안 (초안)', '']
    if not gold_done:
        L += ['> **정확도 미검증 초안.** 사람 정답 라벨 평가 전이다. 숫자는 코드가 센 값, 원인 · 제안은 AI 가설이다.', '']
    else:
        L += ['> **정확도 측정 완료(2026-11-12, 정답 149건, `docs/ai_evaluation_report.md`).** 감성 Accuracy ko 0.76 · ja 0.82 · en 0.68. monetization 주제 Precision은 ja 0.70 · en 0.68 · ko 1.00(2차 검수 v2, 좁은 규칙: 가챠 구조 · 가격을 직접 평가할 때만). AI가 과금 언급을 사람보다 넉넉하게 세므로 과금 수치는 상한으로 읽는다. 원인 · 제안은 AI 가설이다.', '']
    L += [f'생성 {datetime.now():%Y-%m-%d %H:%M} · 내부 KPI는 다루지 않는다 · 근거는 공개 리뷰 발췌', '']
    for lg in ('ko', 'ja', 'en'):
        ids = [k for k, r in R.items() if r['language'] == lg]
        if not ids:
            continue
        neg = [t for t in T if R[t['review_id']]['language'] == lg and t['sentiment'] == 'negative' and t['topic'] != 'other']
        by = collections.Counter(t['topic'] for t in neg)
        dates = sorted(R[i]['review_date'] for i in ids)
        L += [f'## {lg} · {STREAM[lg]}', '', f'리뷰 n={len(ids)} · 기간 {dates[0]} ~ {dates[-1]} · 부정 주제 언급 {len(neg)}건', '']
        for topic, n in by.most_common(a.top):
            ts = [t for t in neg if t['topic'] == topic]
            subs = collections.Counter(G.get((lg, topic, t['sub_topic']), t['sub_topic']) for t in ts).most_common(5)
            ev = [t for t in ts if t['evidence_in_text'] == 'True'][:5]
            data = {'언어 표본': STREAM[lg], '리뷰 수': len(ids), '주제': topic, '부정 언급 수': n,
                    '리뷰 100건당 부정 언급': round(n / len(ids) * 100, 1), '대표 이슈 상위(2차 묶기)': subs,
                    '원문 발췌': [t['evidence'][:200] for t in ev]}
            r = subprocess.run(['claude', '-p', '--model', 'sonnet'], input=PROMPT.format(data=json.dumps(data, ensure_ascii=False, indent=1)),
                               capture_output=True, text=True, encoding='utf-8', timeout=900)
            out = r.stdout
            x = json.loads(out[out.find('{'):out.rfind('}') + 1])
            L += [f'### {topic} — 부정 언급 {n}건 (100건당 {data["리뷰 100건당 부정 언급"]})', '',
                  f'1. **관찰된 문제** {x["observed_problem"]}',
                  f'2. **데이터 근거 · 표본 수** n={len(ids)}, 대표 이슈 ' + ', '.join(f'{s} {c}' for s, c in subs),
                  '3. **원문 근거** ' + ' / '.join(f'「{e["evidence"][:120]}」' for e in ev[:3]),
                  '4. **원인 가설 (AI)** ' + ' / '.join(x['cause_hypotheses']),
                  '5. **추가 확인 정보** ' + ' / '.join(x['info_needed']),
                  f'6. **개선 방향** {x["direction"]}',
                  '7. **실행 과제** ' + ' / '.join(x['action_items']),
                  f'8. **우선순위 (PM 검토용 제안)** {x["priority"]} — {x["priority_reason"]}',
                  f'9. **기대효과 (정성)** {x["expected_effect_qualitative"]}',
                  '10. **리스크** ' + ' / '.join(x['risks']),
                  f'11. **사후 검증** {x["followup_check"]}', '']
            print(lg, topic, n, flush=True)
    open(P('docs', 'business_report_draft.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('saved docs/business_report_draft.md')


if __name__ == '__main__':
    main()

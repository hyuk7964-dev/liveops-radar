"""사람 정답 라벨용 표본 뽑기 (VALIDATION_PLAN 2장).

언어별 50건. main(앱스토어)에서 먼저 뽑고 모자라면 aux(Steam · Gamerch)로 채운다. 별점 낮음/높음이 반반이 되게 층을 나눈다.
AI 결과 열은 넣지 않는다(사람이 AI 답을 보기 전에 라벨링). seed 고정.

사용: python -m src.validation.make_gold_sample  → data/processed/gold_labels.csv
"""
import csv, os, random
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PER_LANG, SEED = 50, 1108


def negative(r):
    return (r['rating'] and int(r['rating']) <= 2) or r['recommended'] == 'False'


def main():
    revs = [r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'processed', 'game_reviews.csv'), encoding='utf-8-sig'))
            if r['analyzable'] == 'True' and r['possible_duplicate'] == 'False']
    rng, out = random.Random(SEED), []
    for lg in ('ko', 'ja', 'en'):
        pick = []
        for role in ('main', 'aux'):
            pool = [r for r in revs if r['language'] == lg and r['role'] == role and r not in pick]
            neg, pos = [r for r in pool if negative(r)], [r for r in pool if not negative(r)]
            rng.shuffle(neg); rng.shuffle(pos)
            need = PER_LANG - len(pick)
            take = neg[:need // 2] + pos[:need - need // 2]
            take += [r for r in neg + pos if r not in take][:need - len(take)]
            pick += take
            if len(pick) >= PER_LANG:
                break
        out += pick
        print(lg, len(pick), {role: sum(1 for r in pick if r['role'] == role) for role in ('main', 'aux')})
    p = os.path.join(ROOT, 'data', 'processed', 'gold_labels.csv')
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['review_id', 'language', 'store', 'role', 'rating_or_recommended', 'review_text',
                    'gold_sentiment', 'gold_topics', 'labeler', 'note'])
        for r in out:
            w.writerow([r['review_id'], r['language'], r['store'], r['role'], r['rating'] or r['recommended'],
                        (r['review_title'] + ' / ' if r['review_title'] else '') + r['review_text'].replace('\n', ' '), '', '', '', ''])
    print(p, len(out))


if __name__ == '__main__':
    main()

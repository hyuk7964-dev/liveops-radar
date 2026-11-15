# LIVEOPS RADAR 웹사이트 (Streamlit). 실행: streamlit run app.py
# 화면 규칙은 VALIDATION_PLAN.md 3장: 숫자 옆 n, 기간, 출처, n < 30 결론 유보(흐리게), 전후 비교는 "날짜 기준 연관 관찰", 원문은 200자 이내 발췌 + 링크
# 분석은 미리 돌려 둔 결과만 읽는다 (화면에서 AI를 다시 부르지 않음). 리뷰는 data/public 발췌본만 읽는다 (원문 CSV 배포 안 함)
# 화면 틀(2026-11-15 결정): 왼쪽 사이드바 버튼으로 섹션 전환, 섹션마다 KPI 띠 + 넓은 차트 + 인사이트 카드. 색은 덱 커버 팔레트(.streamlit/config.toml)
# 인사이트 카드 문장은 docs/ 표현을 쓰고 숫자만 데이터에서 계산해 끼운다. 디자인 시안은 design/ (로컬 전용)
# data/public 갱신: python -X utf8 -m src.reporting.public_data
import json, os, re
import altair as alt
import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, 'data', *a)
MIN_N = 30
GACHA = '개편|50/50|원복|천장|리셋'  # docs/gacha_revamp_matching.md 와 같은 기준
LANG = {'ko': '한국어 Steam', 'ja': '일본어 앱스토어', 'en': '영어 Steam'}
TOPIC = {'monetization': '과금', 'event_ops': '이벤트 운영', 'combat_balance': '전투 밸런스', 'tech_bugs': '기술 오류',
         'content_story': '콘텐츠 스토리', 'growth_resources': '성장 재화', 'character': '캐릭터', 'ui_ux': 'UI UX',
         'customer_support': '고객 응대', 'other': '기타'}
SENT = {'negative': '부정', 'positive': '긍정', 'neutral': '중립', 'mixed': '혼합'}
SECTIONS = ['개요', '언어별 불만 지도', '이슈 탐색', '공지와 반응', '다음 과제', 'AI 정확도', '커뮤니티 온도']
LANG_ORDER = [LANG['ja'], LANG['en'], LANG['ko']]
LANG_COLOR = alt.Scale(domain=LANG_ORDER, range=['#7A8CFF', '#D8FF3F', '#8B95A1'])  # 덱 다크 팔레트 blue, mint(라임), dim
MONTHS = ['8월', '9월', '10월', '11월 초']
# 덱 11장과 같은 과제 표. 2026-11-12 사용자 결정: 일본 운영 불만 P1 → P2 (퍼블리셔 넥슨 이관 과도기 영향)
JA_OPS_P1 = '**우선순위 (PM 검토용 제안)** P1 — 표본은 94건으로 작지만 운영 신뢰와'
JA_OPS_P2 = '**우선순위 (PM 검토용 제안)** P2 (2026-11-12 사용자 결정으로 P1에서 낮춤, 퍼블리셔 넥슨 이관 과도기 영향). AI 초안 원문: 표본은 94건으로 작지만 운영 신뢰와'

st.set_page_config('LIVEOPS RADAR', '📡', layout='wide')
st.markdown("""<style>
[data-testid="stSidebar"]{background:#0A0E13;border-right:1px solid #26303D}
[data-testid="stSidebar"] [role="radiogroup"]{gap:2px}
[data-testid="stSidebar"] [data-testid="stRadioOption"]{padding:10px 14px;border-radius:10px;width:100%;margin:0}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]){display:none}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover{background:#161B22}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]{background:#D8FF3F}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p{color:#0D1117;font-weight:700}
.block-container{padding-top:2.2rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:6px 0 18px}
.kpi{background:#161B22;border:1px solid #26303D;border-radius:12px;padding:14px 16px}
.kpi .l{font-size:12.5px;color:#8B95A1}.kpi .v{font-size:28px;font-weight:800;color:#fff;margin:4px 0 2px;letter-spacing:-.01em}
.kpi .s{font-size:12px;color:#8B95A1;line-height:1.5}.kpi.hold .v{opacity:.4}.kpi.hold .l::after{content:'결론 유보';margin-left:6px;font-size:11px;color:#0D1117;background:#8B95A1;border-radius:4px;padding:1px 5px}
.kpi.hl .v{color:#D8FF3F}
.brand{font-weight:800;letter-spacing:.08em;font-size:17px}.brand i{color:#D8FF3F;font-style:normal}
.ins{background:#161B22;border:1px solid #26303D;border-left:3px solid #D8FF3F;border-radius:14px;padding:18px 20px;margin-bottom:14px}
.ins .t{font-size:12px;letter-spacing:.12em;color:#D8FF3F;font-weight:700;margin-bottom:8px}
.ins p{font-size:14.5px;line-height:1.7;color:#C9D1D9;margin:0 0 6px}
.ins b{color:#fff}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    csv = lambda *a: pd.read_csv(P(*a), encoding='utf-8-sig', dtype=str, keep_default_na=False)
    r = csv('public', 'reviews.csv')
    t = csv('public', 'topics.csv')
    summary = json.load(open(P('public', 'summary.json'), encoding='utf-8'))
    wm = pd.read_csv(P('processed', 'weighted_metrics.csv'), encoding='utf-8-sig')
    imp = json.load(open(P('processed', 'update_impact.json'), encoding='utf-8'))
    tl = csv('reference', 'gacha_revamp_timeline.csv')
    notes = csv('raw', 'community_notes', 'community_notes_kr.csv') if os.path.exists(P('raw', 'community_notes', 'community_notes_kr.csv')) else pd.DataFrame()
    return r, t, wm, imp, tl, notes, summary


def md(name):
    return open(os.path.join(ROOT, 'docs', name), encoding='utf-8').read()


def esc(s):
    """리뷰 발췌 · AI 요약을 markdown에 넣기 전 특수문자 이스케이프 (*, _, $, [ ] 등이 서식으로 바뀌지 않게)"""
    return re.sub(r'([\\`*_{}\[\]()#+\-.!|<>$~])', r'\\\1', str(s))


def ko_topics(text):
    """docs의 영어 주제 키를 화면용 한국어로 (표 칸 '| monetization |' 와 제목 '### monetization —')"""
    for k, v in TOPIC.items():
        text = re.sub(rf'^### {k} — ', f'### {v}, ', text, flags=re.M).replace(f'| {k} |', f'| {v} |')
    return text


def plain(text):
    """docs 원문을 화면에 보일 때만 가운데 점과 줄표를 쉼표로 (docs 파일은 그대로, 2026-11-15 결정)"""
    return re.sub(r'\s*[·—]\s*', ', ', text)


def draft():
    """docs/business_report_draft.md (AI 초안)에 11/12 사용자 결정(일본 운영 P1 → P2)을 반영해 보여 준다"""
    return plain(ko_topics(md('business_report_draft.md').replace(JA_OPS_P1, JA_OPS_P2)))


def eval_report():
    """docs/ai_evaluation_report.md 에서 언어별 정확도, 신뢰도 구간, 과금 2차 검수 표를 읽는다"""
    t = md('ai_evaluation_report.md')
    acc, bands = {}, []
    for l, n, body in re.findall(r'^## (ko|ja|en) \(n=(\d+)\)\n(.*?)(?=^## |\Z)', t, re.M | re.S):
        a, f1 = re.search(r'Accuracy ([\d.]+) · Macro F1 ([\d.]+)', body).groups()
        acc[l] = {'acc': float(a), 'f1': float(f1), 'n': int(n)}
        bands += [{'언어': LANG[l], '신뢰도 구간': b, 'n': int(k), '감성 정답률': float(v)}
                  for b, k, v in re.findall(r'^\| ([\d.]+~[\d.]+) \| (\d+) \| ([\d.]+) \|$', body, re.M)]
    mon = {l: float(p) for l, _, _, p, _, _ in re.findall(r'^\| (ko|ja|en) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$', t, re.M)}
    overall = sum(v['acc'] * v['n'] for v in acc.values()) / sum(v['n'] for v in acc.values())
    return acc, pd.DataFrame(bands), mon, overall


def temperature(notes):
    """주별 커뮤니티 온도(B안). stance: 옹호·긍정 → 긍정, 반발·부정 → 부정, 나머지(중립·혼합·기타) → 기타. 주 = 화요일 시작"""
    stance = notes.stance.map({'옹호': '긍정', '긍정': '긍정', '반발': '부정', '부정': '부정'}).fillna('기타')
    d = pd.to_datetime(notes.post_date)
    wk = (d - pd.to_timedelta((d.dt.weekday - 1) % 7, unit='D')).dt.date.rename('주 시작 (화)')
    s = pd.crosstab(wk, stance, normalize='index').reindex(columns=['긍정', '부정', '기타'], fill_value=0) * 100
    s['온도'] = s['긍정'] + s['기타'] * 0.5 - s['부정'] * 0.5
    s['n'] = wk.value_counts()
    return s.round(1).reset_index()


def gacha_monthly(R, T):
    """월별 가챠 개편 불만 리뷰 비율 (덱 9장과 같은 계산)"""
    hit = T[(T.topic == 'monetization') & T.sentiment.isin(['negative', 'mixed']) & T.issue_group.str.contains(GACHA)].review_id.unique()
    m = R.assign(hit=R.review_id.isin(hit),
                 월=pd.cut(pd.to_datetime(R.review_date).dt.isocalendar().week.astype(int), [0, 35, 39, 44, 99], labels=MONTHS))
    m = m.groupby(['language', '월'], observed=True).hit.agg(['sum', 'count']).reset_index()
    m['비율'] = (m['sum'] / m['count'] * 100).round(1)
    m['언어'] = m.language.map(LANG); m['n'] = m['sum'].astype(str) + '/' + m['count'].astype(str)
    m['표본'] = m['count'].map(lambda n: '결론 유보' if n < MIN_N else '판단 가능')
    return m


def reserved(n):
    return f'n={n}, 결론 유보' if n < MIN_N else f'n={n}'


def head(title, desc):
    st.markdown(f'## {title}')
    st.caption(desc)


def kpis(items):
    """KPI 띠: (라벨, 값, 보조 설명[, n]) 목록. 보조 설명(n, 출처)은 늘 보이게, n < 30이면 흐리게 + 결론 유보 표시"""
    html = ''
    for i, (label, value, sub, *n) in enumerate(items):
        cls = 'kpi hold' if n and n[0] < MIN_N else 'kpi hl' if i == 0 else 'kpi'
        html += f'<div class="{cls}"><div class="l">{label}</div><div class="v">{value}</div><div class="s">{sub}</div></div>'
    st.markdown(f'<div class="kpis">{html}</div>', unsafe_allow_html=True)


def card(title, *paras):
    st.markdown(f'<div class="ins"><div class="t">{title}</div>' + ''.join(f'<p>{p}</p>' for p in paras) + '</div>', unsafe_allow_html=True)


def chart(c, height=360):
    st.altair_chart(c.properties(height=height).configure_view(stroke=None), width='stretch')


R, T, WM, IMP, TL, NOTES, SUMMARY = load()
WMI = WM.set_index(['language', 'topic'])
ACC, BANDS, MON_P, ACC_ALL = eval_report()
neg = lambda l, t: int(WMI.n_negative.get((l, t), 0))

with st.sidebar:
    st.markdown('<div class="brand">LIVEOPS <i>RADAR</i></div>', unsafe_allow_html=True)
    st.caption(f'블루 아카이브 3개 언어 리뷰, 2026.08 ~ 11, 리뷰 {len(R)}건, 공지 {SUMMARY["updates"]}건')
    q = st.query_params.get('s')  # ?s=공지와 반응 처럼 섹션 바로 열기 (공유 링크, 캡처용)
    sec = st.radio('섹션', SECTIONS, index=SECTIONS.index(q) if q in SECTIONS else 0, label_visibility='collapsed', key='section')
    st.divider()
    st.caption(f'숫자는 AI 분류 기준이며 과금은 상한입니다. 사람 정답 {SUMMARY["gold"]}건으로 검증했습니다.')

if (R.is_synthetic == 'True').any():
    st.error('가상 데이터가 섞여 있습니다. 이 화면의 숫자는 실제 분석 결과가 아닙니다.')

# ───────── 개요 ─────────
if sec == '개요':
    head('개요', '블루 아카이브 3개 언어 유저 반응으로 다음 업데이트 과제를 찾는 AI 분석입니다.')
    kpis([('분석한 공개 리뷰', f'{len(R)}건', ', '.join(f'{LANG[l]} {n}' for l, n in R.language.value_counts().items())),
          ('공식 공지', f"{SUMMARY['updates']}건", '넥슨 포럼, 일본 공식, Steam 공지'),
          ('사람 정답 라벨', f"{SUMMARY['gold']}건", '150건 중 의미 없는 리뷰 1건 제외'),
          ('감성 정확도 (정답 기준)', f'{ACC_ALL:.2f}', ', '.join(f"{l} {v['acc']:.2f}" for l, v in ACC.items()) + ' (docs/ai_evaluation_report.md)')])
    left, right = st.columns([3, 1])
    with left:
        d = pd.to_datetime(R.review_date)
        wk = R.assign(주=(d - pd.to_timedelta(d.dt.weekday, unit='D')).dt.date.astype(str), 언어=R.language.map(LANG)).groupby(['주', '언어']).size().reset_index(name='리뷰 수')
        ev = TL[TL.event_date >= wk['주'].min()].assign(주=lambda x: x.event_date)
        bars = alt.Chart(wk).mark_bar().encode(x=alt.X('주:O', title='주 시작일 (월)', axis=alt.Axis(labelAngle=-45)), y=alt.Y('리뷰 수:Q', title='리뷰 수'),
                                                color=alt.Color('언어:N', scale=LANG_COLOR, sort=LANG_ORDER, legend=alt.Legend(orient='top', title=None)),
                                                tooltip=['주', '언어', '리뷰 수'])
        st.markdown('**주별 수집 리뷰 수**')
        chart(bars)
        st.caption(f'리뷰 기간 {R.review_date.min()} ~ {R.review_date.max()}, 출처 Steam 공식 API와 Apple 공개 RSS')
    with right:
        card('표본 읽는 법', '한국어와 영어는 PC 글로벌판 Steam 리뷰라 모바일 이용자 반응과 다를 수 있습니다.',
             '한국 커뮤니티(아카라이브, 디시)는 약관 때문에 자동 수집하지 않고 사람 메모로만 봅니다.')
        card('가장 큰 빈칸', '한국 모바일 이용자와 커뮤니티 반응을 볼 수단이 없는 것이 지금 데이터의 가장 큰 빈칸입니다.')
    src = R.groupby('language').agg(n=('review_id', 'size'), 시작=('review_date', 'min'), 끝=('review_date', 'max'), 수집=('collection_method', 'first')).reset_index()
    src.insert(0, '출처', src.language.map(LANG))
    src['수집'] = src['수집'].map({'steam_official_api': 'Steam 공식 API', 'apple_rss': 'Apple 공개 RSS'}).fillna(src['수집'])
    st.markdown('**무엇을 봤나**')
    st.dataframe(src.drop(columns='language'), hide_index=True, width='stretch')
    st.markdown('**2026년 가챠 개편 타임라인**')
    st.dataframe(TL.replace({'source_type': {'press': '언론', 'official': '공식'}}).rename(columns={'event_date': '날짜', 'region': '지역', 'event': '사건', 'source_type': '출처 종류', 'source_url': '링크'})[['날짜', '지역', '사건', '출처 종류', '링크']],
                 hide_index=True, width='stretch', column_config={'링크': st.column_config.LinkColumn()})  # 출처 종류: press → 언론, official → 공식

# ───────── 언어별 불만 지도 ─────────
elif sec == '언어별 불만 지도':
    head('언어별 불만 지도', '주제별 부정 언급률을 리뷰 100건당으로 셉니다. 부정 언급 30건 미만인 칸은 흐리게 두고 결론을 유보합니다.')
    mode = st.segmented_control('보기', ['공감 가중', '단순 비율'], default='공감 가중', label_visibility='collapsed',
                                help='공감 가중: 리뷰마다 w = 1 + ln(1 + 공감 수). 다른 유저가 동의한 불만을 더 크게 셉니다.')
    weighted = mode != '단순 비율'
    w = WM.copy()
    w['언어'] = w.language.map(LANG); w['주제'] = w.topic.map(TOPIC)
    w['값'] = w.weighted_rate if weighted else w.plain_rate
    w['판정'] = w.n_negative.map(lambda n: '결론 유보' if n < MIN_N else '판단 가능')
    val = lambda l, t: float(w[(w.language == l) & (w.topic == t)]['값'].iloc[0])
    ok = (w.n_negative >= MIN_N).sum()
    kpis([(f"{LANG['ja']} 과금", f"{val('ja', 'monetization'):.1f}", f"100건당, 부정 n={neg('ja', 'monetization')}, 리뷰 {int(WMI.n_reviews[('ja', 'monetization')])}건", neg('ja', 'monetization')),
          (f"{LANG['en']} 과금", f"{val('en', 'monetization'):.1f}", f"100건당, 부정 n={neg('en', 'monetization')}, 리뷰 {int(WMI.n_reviews[('en', 'monetization')])}건", neg('en', 'monetization')),
          (f"{LANG['ko']} 과금", f"{val('ko', 'monetization'):.1f}", f"100건당, 부정 n={neg('ko', 'monetization')}, 리뷰 {int(WMI.n_reviews[('ko', 'monetization')])}건", neg('ko', 'monetization')),
          ('판단 가능한 칸', f'{ok} / {w.topic.nunique() * len(LANG)}', '부정 언급 30건 이상인 언어 × 주제 칸')])
    left, right = st.columns([3, 1])
    with left:
        st.markdown(f"**주제별 부정 언급률 ({mode}, 100건당)**")
        base = alt.Chart(w).encode(y=alt.Y('주제:N', sort=[TOPIC[k] for k in TOPIC], title=None), yOffset=alt.YOffset('언어:N', sort=LANG_ORDER))
        bars = base.mark_bar(cornerRadiusEnd=3).encode(x=alt.X('값:Q', title='100건당'), color=alt.Color('언어:N', scale=LANG_COLOR, sort=LANG_ORDER, legend=alt.Legend(orient='top', title=None)),
                                                       opacity=alt.condition('datum.판정 == "결론 유보"', alt.value(0.3), alt.value(1)),
                                                       tooltip=['언어', '주제', '값', alt.Tooltip('n_negative', title='부정 n'), alt.Tooltip('n_reviews', title='리뷰 n'), '판정'])
        text = base.mark_text(align='left', dx=4, fontSize=11, color='#C9D1D9').encode(x='값:Q', text=alt.Text('값:Q', format='.1f'))
        chart(bars + text, 520)
        st.caption('흐린 막대는 부정 언급 30건 미만이라 결론 유보입니다. 출처 docs/weighted_metrics.md')
    with right:
        card('INSIGHT', f"과금 부정 언급은 {LANG['ja']} {val('ja', 'monetization'):.1f}, {LANG['en']} {val('en', 'monetization'):.1f} (100건당)입니다. 나머지 칸은 부정 30건 미만이라 결론 유보입니다.",
             f"영어 과금 부정 {neg('en', 'monetization')}건의 공감 배율은 {WMI.vote_lift[('en', 'monetization')]:.2f}, 장기 이용자 비중은 {WMI.long_player_share[('en', 'monetization')]:.1f}%입니다.")
        card('읽는 법', f"AI가 과금 언급을 사람보다 넉넉하게 세므로 과금 수치는 상한으로 읽습니다. 과금 정밀도 ja {MON_P['ja']:.2f}, en {MON_P['en']:.2f}.")
    st.markdown('**누가 불만인가**')
    st.dataframe(w[['언어', '주제', 'n_negative', 'vote_lift', 'long_player_share', 'playtime_median_h', '판정']].rename(
        columns={'n_negative': '부정 n', 'vote_lift': '공감 배율', 'long_player_share': '장기 이용자 비중 %', 'playtime_median_h': '플레이 시간 중앙값 h'}),
        hide_index=True, width='stretch')
    st.caption('공감 배율은 가중률 ÷ 단순률이며 1보다 크면 다른 유저가 더 동의한 불만입니다. 장기 이용자 비중은 중앙값 기준이라 50%가 중립입니다. 앱스토어는 플레이 시간이 없습니다. 상관 관찰로만 읽습니다.')

# ───────── 이슈 탐색 ─────────
elif sec == '이슈 탐색':
    head('이슈 탐색', '언어와 주제를 고르면 AI가 묶은 대표 이슈와 원문 발췌를 보여 줍니다.')
    c = st.columns(3)
    lg = c[0].selectbox('언어', list(LANG), format_func=LANG.get)
    tp = c[1].selectbox('주제', list(TOPIC), format_func=TOPIC.get)
    sn = c[2].multiselect('감성', list(SENT), ['negative', 'mixed'], format_func=SENT.get)
    sel = T[(T.language == lg) & (T.topic == tp) & T.sentiment.isin(sn)]
    n_sel, n_all = sel.review_id.nunique(), int((R.language == lg).sum())
    grp = sel.drop_duplicates(['review_id', 'issue_group']).issue_group.replace('', '미분류').value_counts().rename_axis('대표 이슈').reset_index(name='리뷰 수')
    kpis([('해당 리뷰', f'{n_sel}건', f'n={n_sel}', n_sel), (f'{LANG[lg]} 전체', f'{n_all}건', '이 언어 표본 전체'),
          ('비율', f'{n_sel / n_all * 100:.1f}%' if n_all else '-', '해당 리뷰 ÷ 전체'), ('대표 이슈 수', f'{len(grp)}개', 'AI 분류 뒤 2차 묶기 결과')])
    if len(grp):
        left, right = st.columns([3, 1])
        with left:
            st.markdown(f'**{LANG[lg]} {TOPIC[tp]} 대표 이슈 (상위 10)**')
            chart(alt.Chart(grp.head(10)).mark_bar(color='#D8FF3F', cornerRadiusEnd=3).encode(
                x=alt.X('리뷰 수:Q', axis=alt.Axis(tickMinStep=1, format='d')), y=alt.Y('대표 이슈:N', sort='-x', title=None), tooltip=['대표 이슈', '리뷰 수']), 320)
        with right:
            top = grp.iloc[0]
            card('INSIGHT', f"가장 많은 대표 이슈는 <b>{top['대표 이슈']}</b> {top['리뷰 수']}건입니다 ({reserved(n_sel)}).",
                 '대표 이슈는 AI 분류 뒤 2차 묶기 결과입니다 (src/analysis/cluster_issues.py).')
        g = st.selectbox('원문 발췌 볼 이슈', grp['대표 이슈'])
        ids = sel[sel.issue_group.replace('', '미분류') == g].review_id.unique()
        for _, x in R[R.review_id.isin(ids)].sort_values('review_date', ascending=False).head(10).iterrows():
            with st.container(border=True):
                st.markdown(f'「{esc(x.excerpt)}」')
                st.caption(f'AI 요약: {esc(x.issue_summary)}, {x.review_date}, 공감 {x.votes_up or 0}, [출처]({x.source_url})')
        st.caption('원문은 200자 이내 발췌입니다.')
    else:
        st.info('해당 조건의 리뷰가 없습니다.')

# ───────── 공지와 반응 ─────────
elif sec == '공지와 반응':
    head('공지와 반응', '가챠 개편 불만 리뷰 비율을 공지 날짜와 나란히 봅니다. 날짜 기준 연관 관찰입니다.')
    m = gacha_monthly(R, T)
    g = lambda l, mo: m[(m.language == l) & (m.월 == mo)].iloc[0]
    ja8, en8, en10 = g('ja', '8월'), g('en', '8월'), g('en', '10월')
    ko = m[m.language == 'ko'][['sum', 'count']].sum()
    kpis([(f"{LANG['ja']} 8월", f"{ja8['비율']:.0f}%", f"{ja8['n']}건, n={int(ja8['count'])}", int(ja8['count'])),
          (f"{LANG['en']} 8월 → 10월", f"{en8['비율']:.0f}% → {en10['비율']:.0f}%", f"{en8['n']} → {en10['n']}건"),
          (f"{LANG['ko']} 합계", f"{int(ko['sum'])} / {int(ko['count'])}", '이 표본에는 이 이슈가 거의 없습니다'),
          ('공식 공지', f"{SUMMARY['updates']}건", '넥슨 포럼, 일본 공식, Steam 공지')])
    left, right = st.columns([3, 1])
    with left:
        st.markdown('**월별 가챠 개편 불만 리뷰 비율 (날짜 기준 연관 관찰)**')
        chart(alt.Chart(m).mark_bar(cornerRadiusEnd=3).encode(
            x=alt.X('월:N', sort=MONTHS, title=None, axis=alt.Axis(labelAngle=0)), xOffset=alt.XOffset('언어:N', sort=LANG_ORDER),
            y=alt.Y('비율:Q', title='%'),
            color=alt.Color('언어:N', scale=LANG_COLOR, sort=LANG_ORDER, legend=alt.Legend(orient='top', title=None)),
            opacity=alt.condition('datum.표본 == "결론 유보"', alt.value(0.3), alt.value(1)),
            tooltip=['언어', '월', '비율', 'n', '표본']))
        st.caption('주 구간은 8월 W32부터 W35, 9월 W36부터 W39, 10월 W40부터 W44, 11월 초 W45입니다. 일본어 9월은 Apple RSS 수집 공백이며 불만이 없었다는 뜻으로 읽지 않습니다. 흐린 막대는 그 달 리뷰 30건 미만입니다. 출처 docs/gacha_revamp_matching.md')
    with right:
        card('INSIGHT', f"일본 앱스토어와 Steam 영어는 7/29 일본 개편 직후가 가장 높습니다 (일본 8월 {ja8['비율']:.0f}%, 영어 8월 {en8['비율']:.0f}%). 이후 줄어듭니다.",
             '10/08 글로벌 사전 안내 뒤 Steam 영어 리뷰에 다시 오르는 움직임은 보이지 않습니다.',
             f"Steam 한국어 리뷰에는 이 이슈가 거의 없습니다 ({int(ko['sum'])}/{int(ko['count'])}).")
        card('사후 검증', '기준일 2026-11-10 (한국, 글로벌 적용). 11/10 앞뒤 14일 비율이 8월 수준까지 오르는지 2026-11-24 이후 확인합니다.')
    st.markdown('**공지별 전후 14일**')
    st.caption('같은 기간 다른 공지(교란 요인)를 함께 표시합니다. 전후 차이는 날짜 기준 연관 관찰로만 읽습니다.')
    for x in IMP:
        pre, post = x['pre'], x['post']
        with st.expander(f"{x['base_date']}, {x['stream']}, {x['title']}"):
            c = st.columns(2)
            c[0].metric(f"이전 14일 부정 비율 ({reserved(pre['n'])})", f"{pre['neg_ratio'] * 100:.0f}%")
            c[1].metric(f"이후 14일 부정 비율 ({reserved(post['n'])})", f"{post['neg_ratio'] * 100:.0f}%", f"{(post['neg_ratio'] - pre['neg_ratio']) * 100:+.0f}%p", delta_color='inverse')
            if not x['enough_sample']:
                st.caption('전후 한쪽이라도 표본이 부족해 차이를 판단하지 않습니다.')
            if x['confounders']:
                st.caption('같은 기간 다른 공지: ' + ' / '.join(x['confounders'][:5]))
            if x.get('source_url'):
                st.caption(f"[공지 출처]({x['source_url']})")

# ───────── 다음 과제 ─────────
elif sec == '다음 과제':
    head('다음 과제', 'AI 초안을 사람이 검토한 PM 검토용 제안입니다. 원인은 AI 가설이며 내부 매출과 이탈 지표 확인이 먼저입니다.')
    combat = [neg(l, 'combat_balance') for l in LANG]
    tasks = pd.DataFrame([
        ('P1', '일본, 영어', f"가챠 개편이 손해로 받아들여짐. 과금 부정 일본 {neg('ja', 'monetization')}건, 영어 {neg('en', 'monetization')}건", '개편 전후 획득 구조를 한 장으로 비교하는 안내 (천장 포인트 처리 포함)', '100건당 과금 부정 언급 재측정', neg('ja', 'monetization') + neg('en', 'monetization')),
        ('P1', '영어', f"접속 세션 오류로 플레이 불가. 기술 부정 {neg('en', 'tech_bugs')}건 중 6건. 건수는 적지만 지켜볼 신호", '재현 조건 확인 요청과 오류 안내 문구 개선', '세션 오류 언급 수', neg('en', 'tech_bugs')),
        ('P2', '일본', f"공지 방식과 침묵에 대한 불신. 운영 부정 {neg('ja', 'event_ops')}건. 퍼블리셔가 넥슨으로 바뀌는 과도기 영향 (11/12 결정으로 P1에서 P2)", '이관 뒤 공지 채널과 사과 공지 틀 정비', '이관 뒤 운영 부정 언급 변화', neg('ja', 'event_ops')),
        ('P2', '한국어', f"확률 천장 불신과 월정액 부담. 과금 부정 {neg('ko', 'monetization')}건", '확률과 천장과 재화 수급처를 한눈에 보는 안내', '같은 표본 재수집 비교', neg('ko', 'monetization')),
        ('P2', '공통', f"전투 단조로움과 자동전투 깊이 부족. 언어별 {min(combat)} ~ {max(combat)}건", '원문 재분류 뒤 콘텐츠 구간을 좁혀 판단', '다음 수집 주기 재확인', sum(combat)),
    ], columns=['우선순위', '대상', '문제', '제안', '확인 지표', '근거 부정 n'])
    tasks.insert(2, '과제', ['가챠 소통', '접속 오류', '운영 소통', '확률 안내', '전투 깊이'])
    kpis([('P1 과제', f"{(tasks.우선순위 == 'P1').sum()}건", '조기 확인 제안'), ('P2 과제', f"{(tasks.우선순위 == 'P2').sum()}건", '원인 확인 뒤 단계적 개선'),
          ('근거 리뷰', f'{len(R)}건', '공개 리뷰 3개 언어'), ('일본 운영 불만', 'P1 → P2', '2026-11-12 사용자 결정')])
    left, right = st.columns([3, 1])
    with left:
        st.markdown('**과제별 근거 부정 리뷰 수**')
        tk = tasks.assign(과제=tasks.우선순위 + ' ' + tasks.대상 + ' ' + tasks.과제, 판정=tasks['근거 부정 n'].map(lambda n: '결론 유보' if n < MIN_N else '판단 가능'))
        bars = alt.Chart(tk).mark_bar(cornerRadiusEnd=3).encode(x=alt.X('근거 부정 n:Q'), y=alt.Y('과제:N', sort=None, title=None, axis=alt.Axis(labelLimit=240)),
                                                               color=alt.Color('우선순위:N', scale=alt.Scale(domain=['P1', 'P2'], range=['#D8FF3F', '#7A8CFF']), legend=alt.Legend(orient='top', title=None)),
                                                               opacity=alt.condition('datum.판정 == "결론 유보"', alt.value(0.35), alt.value(1)),
                                                               tooltip=['우선순위', '대상', '문제', '근거 부정 n', '판정'])
        chart(bars + bars.mark_text(align='left', dx=4, color='#C9D1D9').encode(text='근거 부정 n:Q', opacity=alt.value(1)), 280)
        st.caption('흐린 막대는 근거 부정 30건 미만입니다. 영어 접속 오류는 건수가 적어도 플레이를 막는 문제라 P1으로 지켜봅니다.')
    with right:
        card('제안 요약', 'P1은 일본과 영어권의 가챠 소통으로 개편 전후 획득 구조를 한 장으로 비교하는 안내입니다.',
             '영어 접속 오류는 건수가 적지만 플레이 불가 문제라 P1으로 지켜봅니다.',
             '일본 운영 불만은 퍼블리셔 이관 과도기 영향으로 보고 P2로 내렸습니다.')
        card('먼저 확인할 것', '모든 제안은 내부 매출과 이탈 지표 확인이 먼저입니다.')
    st.dataframe(tasks, hide_index=True, width='stretch')
    with st.expander('AI 초안 전문 (docs/business_report_draft.md)'):
        st.caption('AI 초안 작성 시점(11/08)의 숫자라 위 표(정답 검수 뒤 지표)와 다를 수 있습니다. 일본 운영 우선순위는 11/12 결정을 반영했습니다.')
        st.markdown(draft())

# ───────── AI 정확도 ─────────
elif sec == 'AI 정확도':
    head('AI 정확도', f"사람이 직접 단 정답 {SUMMARY['gold']}건과 AI 분류를 비교했습니다.")
    kpis([(f'{LANG[l]} 감성 정확도', f"{v['acc']:.2f}", f"정답 n={v['n']}, Macro F1 {v['f1']:.2f}") for l, v in ACC.items()] +
         [('과금 정밀도 (2차 검수)', f"ja {MON_P['ja']:.2f}, en {MON_P['en']:.2f}", f"ko {MON_P['ko']:.2f}. 좁은 규칙: 가챠 구조와 가격을 직접 평가할 때만 과금")])
    left, right = st.columns([3, 1])
    with left:
        st.markdown('**언어별 감성 정확도 (사람 정답 기준)**')
        a = pd.DataFrame([{'언어': LANG[l], '정확도': v['acc'], 'n': v['n'], '판정': '결론 유보' if v['n'] < MIN_N else '판단 가능'} for l, v in ACC.items()])
        a['라벨'] = a.정확도.map('{:.2f}'.format) + ' (n=' + a.n.astype(str) + ')'
        base = alt.Chart(a).encode(x=alt.X('언어:N', sort=LANG_ORDER, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y('정확도:Q', scale=alt.Scale(domain=[0, 1]), title='감성 정확도'))
        bars = base.mark_bar(cornerRadiusEnd=4, size=90).encode(color=alt.Color('언어:N', scale=LANG_COLOR, sort=LANG_ORDER, legend=None),
                                                               opacity=alt.condition('datum.판정 == "결론 유보"', alt.value(0.3), alt.value(1)), tooltip=['언어', '정확도', 'n', '판정'])
        chart(bars + base.mark_text(dy=-10, fontSize=13, color='#FFFFFF').encode(text='라벨:N'))
        st.caption('정답 30건 미만이면 흐리게 표시하고 결론을 유보합니다. 출처 docs/ai_evaluation_report.md')
        with st.expander('AI 신뢰도 구간별 감성 정답률'):
            st.dataframe(BANDS.assign(판정=BANDS.n.map(lambda n: '결론 유보' if n < MIN_N else '판단 가능')), hide_index=True, width='stretch')
    with right:
        card('INSIGHT', '감성 정확도 ' + ', '.join(f"{l} {v['acc']:.2f}" for l, v in ACC.items()) + '.',
             f"과금 정밀도(2차 검수) ja {MON_P['ja']:.2f}, en {MON_P['en']:.2f}, ko {MON_P['ko']:.2f}. AI가 과금 언급을 사람보다 넉넉하게 세므로 과금 수치는 상한으로 읽습니다.")
        card('원인과 제안', '원인과 제안은 AI 가설입니다. 사람이 검토한 뒤 PM 검토용으로만 씁니다.')
    with st.expander('평가 리포트 전문 (주제별 Precision, Recall, F1)'):
        st.markdown(plain(ko_topics(md('ai_evaluation_report.md'))))

# ───────── 커뮤니티 온도 ─────────
elif sec == '커뮤니티 온도':
    head('커뮤니티 온도', '한국 커뮤니티 반응을 사람 메모로 기록해 주별 온도를 계산합니다. 업데이트 요일(블루 아카이브 한국 화요일)로 주를 나눕니다.')
    t = temperature(NOTES) if not NOTES.empty else pd.DataFrame()
    kpis([('메모 수', f'{len(NOTES)}건', '사람이 고른 표본, 주 20~30건 목표'), ('기록된 주', f'{len(t)}주', '주 시작 = 화요일'),
          ('최근 주 온도', f"{t['온도'].iloc[-1]:.1f}도" if len(t) else '대기', reserved(int(t['n'].iloc[-1])) if len(t) else '메모 입력 대기'),
          ('수집 방식', '사람 메모', '약관 때문에 자동 수집하지 않음')])
    left, right = st.columns([3, 1])
    with left:
        st.markdown('**주별 커뮤니티 온도**')
        if len(t):
            t['판정'] = t['n'].map(lambda n: '결론 유보' if n < MIN_N else '판단 가능')
            t['주'] = t['주 시작 (화)'].astype(str)
            chart(alt.Chart(t).mark_bar(color='#D8FF3F', cornerRadiusEnd=3).encode(x=alt.X('주:O', title='주 시작 (화)'), y=alt.Y('온도:Q', scale=alt.Scale(domain=[-50, 100])),
                                                                                   opacity=alt.condition('datum.판정 == "결론 유보"', alt.value(0.35), alt.value(1)), tooltip=['주', '온도', '긍정', '부정', '기타', 'n', '판정']))
        else:
            st.info('메모 입력 대기: data/raw/community_notes/community_notes_kr.csv 에 메모가 들어오면 주별 온도가 여기에 계산됩니다.')
    with right:
        card('온도 계산', '<b>온도 = 긍정 + 기타 × 0.5 − 부정 × 0.5</b>', '각 비중은 %이고 범위는 −50 ~ 100도입니다. 예를 들어 70 / 20 / 10이면 65도입니다.')
        card('읽는 법', '사람이 고른 표본(주 20~30건)이라 오차가 큽니다 (n=25면 약 ±20%p). 비율로 대표성을 주장하지 않습니다.')
    if len(t):
        st.dataframe(t.drop(columns=['주']), hide_index=True, width='stretch')
        st.dataframe(NOTES[['post_date', 'site', 'topic', 'stance', 'my_summary', 'post_url']], hide_index=True, width='stretch',
                     column_config={'post_url': st.column_config.LinkColumn('링크')})

st.divider()
st.caption('데이터는 Steam 공식 API, Apple 공개 RSS, 공식 공지입니다. 원문 리뷰는 공개 배포하지 않으며 블루 아카이브 공식 에셋을 쓰지 않습니다.')

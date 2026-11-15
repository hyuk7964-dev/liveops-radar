# LIVEOPS RADAR 웹사이트 (Streamlit). 실행: streamlit run app.py
# 화면 규칙은 VALIDATION_PLAN.md 3장: 숫자 옆 n · 기간 · 출처, n < 30 결론 유보, 전후 비교는 "날짜 기준 연관 관찰", 원문은 200자 이내 발췌 + 링크
# 분석은 미리 돌려 둔 결과만 읽는다 (화면에서 AI를 다시 부르지 않음). 리뷰는 data/public 발췌본만 읽는다 (원문 CSV 배포 안 함)
# data/public 갱신: python -X utf8 -m src.reporting.public_data
import json, os
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

st.set_page_config('LIVEOPS RADAR', '📡', layout='wide')


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


def temperature(notes):
    """주별 커뮤니티 온도(B안). stance: 옹호·긍정 → 긍정, 반발·부정 → 부정, 나머지(중립·혼합·기타) → 기타. 주 = 화요일 시작"""
    stance = notes.stance.map({'옹호': '긍정', '긍정': '긍정', '반발': '부정', '부정': '부정'}).fillna('기타')
    d = pd.to_datetime(notes.post_date)
    wk = (d - pd.to_timedelta((d.dt.weekday - 1) % 7, unit='D')).dt.date.rename('주 시작 (화)')
    s = pd.crosstab(wk, stance, normalize='index').reindex(columns=['긍정', '부정', '기타'], fill_value=0) * 100
    s['온도'] = s['긍정'] + s['기타'] * 0.5 - s['부정'] * 0.5
    s['n'] = wk.value_counts()
    return s.round(1).reset_index()


def reserved(n):
    return f'n={n} · 결론 유보' if n < MIN_N else f'n={n}'


R, T, WM, IMP, TL, NOTES, SUMMARY = load()
if (R.is_synthetic == 'True').any():
    st.error('가상 데이터가 섞여 있습니다. 이 화면의 숫자는 실제 분석 결과가 아닙니다.')

st.title('📡 LIVEOPS RADAR')
st.caption('블루 아카이브 3개 언어 유저 반응으로 다음 업데이트 과제를 찾는 AI 분석 · 리뷰 기간 2026.08 ~ 11 · 숫자는 AI 분류 기준이며 과금은 상한')

tabs = st.tabs(['개요', '언어별 불만 지도', '이슈 탐색', '공지와 반응', '다음 과제', 'AI 정확도', '커뮤니티 온도'])

# ───────── 개요 ─────────
with tabs[0]:
    c = st.columns(4)
    c[0].metric('분석한 공개 리뷰', f'{len(R)}건')
    c[1].metric('공식 공지', f"{SUMMARY['updates']}건", help='넥슨 포럼 + 일본 공식 + Steam 공지')
    c[2].metric('사람 정답 라벨', f"{SUMMARY['gold']}건", help='150건 중 의미 없는 리뷰 1건 제외')
    c[3].metric('감성 정확도 (정답 기준)', '0.75', help=f"정답 {SUMMARY['gold']}건 · 언어별 ko 0.76 · ja 0.82 · en 0.68 (docs/ai_evaluation_report.md)")
    src = R.groupby('language').agg(n=('review_id', 'size'), 시작=('review_date', 'min'), 끝=('review_date', 'max'), 수집=('collection_method', 'first')).reset_index()
    src.insert(0, '출처', src.language.map(LANG))
    src['수집'] = src['수집'].map({'steam_official_api': 'Steam 공식 API', 'apple_rss': 'Apple 공개 RSS'}).fillna(src['수집'])
    st.subheader('무엇을 봤나')
    st.dataframe(src.drop(columns='language'), hide_index=True, width='stretch')
    st.info('한국어와 영어는 PC 글로벌판 Steam 리뷰라 모바일 이용자 반응과 다를 수 있습니다. '
            '한국 커뮤니티(아카라이브 디시)는 약관 때문에 자동 수집하지 않고 사람 메모로만 봅니다.')
    st.subheader('2026년 가챠 개편 타임라인')
    st.dataframe(TL.rename(columns={'event_date': '날짜', 'region': '지역', 'event': '사건', 'source_type': '출처 종류', 'source_url': '링크'})[['날짜', '지역', '사건', '출처 종류', '링크']],
                 hide_index=True, width='stretch', column_config={'링크': st.column_config.LinkColumn()})

# ───────── 언어별 불만 지도 ─────────
with tabs[1]:
    st.subheader('주제별 부정 언급률 (리뷰 100건당)')
    weighted = st.toggle('공감 가중으로 보기', True, help='리뷰마다 w = 1 + ln(1 + 공감 수). 다른 유저가 동의한 불만을 더 크게 센다.')
    w = WM.copy()
    w['언어'] = w.language.map(LANG); w['주제'] = w.topic.map(TOPIC)
    w['값'] = w.weighted_rate if weighted else w.plain_rate
    w['판정'] = w.n_negative.map(lambda n: '결론 유보' if n < MIN_N else '판단 가능')
    base = alt.Chart(w).encode(x=alt.X('언어:N', sort=list(LANG.values()), title=None, axis=alt.Axis(labelAngle=0, orient='top')),
                               y=alt.Y('주제:N', sort=[TOPIC[k] for k in TOPIC], title=None))
    heat = base.mark_rect().encode(color=alt.Color('값:Q', scale=alt.Scale(scheme='blues'), title='100건당'),
                                   opacity=alt.condition('datum.판정 == "결론 유보"', alt.value(0.3), alt.value(1)),
                                   tooltip=['언어', '주제', '값', 'n_negative', 'n_reviews', '판정'])
    text = base.mark_text(fontSize=13).encode(text=alt.Text('값:Q', format='.1f'),
                                              color=alt.condition('datum.값 > 25', alt.value('white'), alt.value('black')))
    st.altair_chart((heat + text).properties(height=380), width='stretch')
    st.caption('흐린 칸 = 부정 언급 30건 미만이라 결론 유보 · 과금 숫자는 AI 상한 (과금 정밀도 ja 0.70 en 0.68) · 출처 docs/weighted_metrics.md')
    st.subheader('누가 불만인가')
    st.dataframe(w[['언어', '주제', 'n_negative', 'vote_lift', 'long_player_share', 'playtime_median_h', '판정']].rename(
        columns={'n_negative': '부정 n', 'vote_lift': '공감 배율', 'long_player_share': '장기 이용자 비중 %', 'playtime_median_h': '플레이 시간 중앙값 h'}),
        hide_index=True, width='stretch')
    st.caption('공감 배율 = 가중률 ÷ 단순률 (1보다 크면 다른 유저가 더 동의) · 장기 이용자 비중은 중앙값 기준이라 50%가 중립 · 앱스토어는 플레이 시간 없음 · 상관 관찰이며 인과 아님')

# ───────── 이슈 탐색 ─────────
with tabs[2]:
    c = st.columns(3)
    lg = c[0].selectbox('언어', list(LANG), format_func=LANG.get)
    tp = c[1].selectbox('주제', list(TOPIC), format_func=TOPIC.get)
    sn = c[2].multiselect('감성', list(SENT), ['negative', 'mixed'], format_func=SENT.get)
    sel = T[(T.language == lg) & (T.topic == tp) & T.sentiment.isin(sn)]
    n_all = (R.language == lg).sum()
    st.markdown(f'**{LANG[lg]} {TOPIC[tp]}** · 해당 리뷰 {sel.review_id.nunique()}건 / 전체 {n_all}건 ({reserved(sel.review_id.nunique())})')
    grp = sel.drop_duplicates(['review_id', 'issue_group']).issue_group.replace('', '미분류').value_counts().rename_axis('대표 이슈').reset_index(name='리뷰 수')
    if len(grp):
        st.altair_chart(alt.Chart(grp.head(10)).mark_bar(color='#3D5AFE').encode(x=alt.X('리뷰 수:Q', axis=alt.Axis(tickMinStep=1, format='d')), y=alt.Y('대표 이슈:N', sort='-x', title=None), tooltip=['대표 이슈', '리뷰 수']),
                        width='stretch')
        g = st.selectbox('원문 발췌 볼 이슈', grp['대표 이슈'])
        ids = sel[sel.issue_group.replace('', '미분류') == g].review_id.unique()
        for _, x in R[R.review_id.isin(ids)].sort_values('review_date', ascending=False).head(10).iterrows():
            with st.container(border=True):
                st.markdown(f'「{x.excerpt}」')
                st.caption(f'AI 요약: {x.issue_summary} · {x.review_date} · 공감 {x.votes_up or 0} · [출처]({x.source_url})')
    else:
        st.write('해당 조건의 리뷰가 없습니다.')
    st.caption('대표 이슈 = AI 분류 뒤 2차 묶기 결과 (src/analysis/cluster_issues.py) · 원문은 200자 이내 발췌')

# ───────── 공지와 반응 ─────────
with tabs[3]:
    st.subheader('가챠 개편 불만 비율 · 날짜 기준 연관 관찰')
    hit = T[(T.topic == 'monetization') & T.sentiment.isin(['negative', 'mixed']) & T.issue_group.str.contains(GACHA)].review_id.unique()
    m = R.assign(hit=R.review_id.isin(hit),
                 월=pd.cut(pd.to_datetime(R.review_date).dt.isocalendar().week.astype(int), [0, 35, 39, 44, 99], labels=['8월', '9월', '10월', '11월 초']))
    m = m.groupby(['language', '월'], observed=True).hit.agg(['sum', 'count']).reset_index()
    m['비율'] = (m['sum'] / m['count'] * 100).round(1)
    m['언어'] = m.language.map(LANG); m['n'] = m['sum'].astype(str) + '/' + m['count'].astype(str)
    m['표본'] = m['count'].map(lambda n: '결론 유보' if n < MIN_N else '판단 가능')
    st.altair_chart(alt.Chart(m).mark_bar().encode(
        x=alt.X('월:N', sort=['8월', '9월', '10월', '11월 초'], title=None, axis=alt.Axis(labelAngle=0)), xOffset=alt.XOffset('언어:N', sort=[LANG['ja'], LANG['en'], LANG['ko']]),
        y=alt.Y('비율:Q', title='%'),
        color=alt.Color('언어:N', scale=alt.Scale(domain=[LANG['ja'], LANG['en'], LANG['ko']], range=['#3D5AFE', '#0D1117', '#8B95A1'])),  # 덱 9장과 같은 색
        opacity=alt.condition('datum.표본 == "결론 유보"', alt.value(0.3), alt.value(1)),
        tooltip=['언어', '월', '비율', 'n', '표본']).properties(height=320), width='stretch')
    st.caption('주 구간: 8월 W32–35 · 9월 W36–39 · 10월 W40–44 · 11월 초 W45 · 일본어 9월은 Apple RSS 수집 공백(불만이 없었다는 뜻 아님) · 흐린 막대 = 그 달 리뷰 30건 미만 · 출처 docs/gacha_revamp_matching.md')
    st.subheader('공지별 전후 14일')
    st.caption('공지가 반응을 만들었다고 단정하지 않습니다. 같은 기간 다른 공지(교란 요인)를 함께 표시합니다.')
    for x in IMP:
        pre, post = x['pre'], x['post']
        with st.expander(f"{x['base_date']} · {x['stream']} · {x['title']}"):
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
with tabs[4]:
    st.warning('AI 초안을 사람이 검토한 PM 검토용 제안입니다. 원인은 AI 가설이며 내부 매출과 이탈 지표 확인이 먼저입니다.')
    st.markdown(md('business_report_draft.md'))

# ───────── AI 정확도 ─────────
with tabs[5]:
    st.markdown(md('ai_evaluation_report.md'))

# ───────── 커뮤니티 온도 ─────────
with tabs[6]:
    st.subheader('한국 커뮤니티 온도 (사람 메모 기준)')
    st.markdown('**온도 = 긍정 + 기타 × 0.5 − 부정 × 0.5** (각 비중 %, 범위 −50 ~ 100, 예 70 / 20 / 10 → 65도) · 주 시작 = 업데이트 요일(블루 아카이브 한국 화요일)')
    if NOTES.empty:
        st.info('메모 입력 대기: data/raw/community_notes/community_notes_kr.csv 에 메모가 들어오면 주별 온도가 여기에 계산됩니다.')
    else:
        st.dataframe(temperature(NOTES), hide_index=True, width='stretch')
        st.caption('사람이 고른 표본(주 20~30건)이라 오차가 큽니다 (n=25면 약 ±20%p). 비율로 대표성을 주장하지 않습니다. 관심도(그 주 글 수 ÷ 전주 글 수)는 주별 글 수 기록이 생기면 추가합니다.')
        st.dataframe(NOTES[['post_date', 'site', 'topic', 'stance', 'my_summary', 'post_url']], hide_index=True, width='stretch',
                     column_config={'post_url': st.column_config.LinkColumn('링크')})

st.divider()
st.caption('데이터: Steam 공식 API · Apple 공개 RSS · 공식 공지 · 원문 리뷰는 공개 배포하지 않습니다 · 블루 아카이브 공식 에셋을 쓰지 않습니다')

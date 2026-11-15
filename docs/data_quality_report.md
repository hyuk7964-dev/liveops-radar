# 데이터 품질 리포트

생성: 2026-11-12 18:25 · 도구 `src/validation/validate.py` · 기준 VALIDATION_PLAN.md

## 1. 파일별 검사

| 파일 | 종류 | 행 | 실제/가상 | 오류 |
|---|---|---|---|---|
| `data\raw\community_notes\community_notes_kr.csv` | None | 0 | 혼합 | 1 |
| `data\raw\reviews\appstore_jp_20261108.csv` | reviews | 100 | 실제 | 0 |
| `data\raw\reviews\appstore_kr_20261108.csv` | reviews | 100 | 실제 | 0 |
| `data\raw\reviews\appstore_us_20261108.csv` | reviews | 0 | 혼합 | 0 |
| `data\raw\reviews\gamerch_jp_20261108.csv` | reviews | 34 | 실제 | 0 |
| `data\raw\reviews\steam_global_english_20261108.csv` | reviews | 417 | 실제 | 0 |
| `data\raw\reviews\steam_global_koreana_20261108.csv` | reviews | 267 | 실제 | 1 |
| `data\raw\updates\updates_global_steam_20261108.csv` | updates | 49 | 실제 | 0 |
| `data\raw\updates\updates_jp_manual.csv` | updates | 6 | 실제 | 0 |
| `data\raw\updates\updates_kr_manual.csv` | updates | 10 | 실제 | 0 |
| `data\sample\synthetic_reviews.csv` | reviews | 6 | 가상 | 0 |

**data\raw\community_notes\community_notes_kr.csv 오류 (처음 20개)**

- review_id 또는 update_id 열이 없음

**data\raw\reviews\steam_global_koreana_20261108.csv 오류 (처음 20개)**

- 188행: review_text 비어 있음

## 2. 실제 리뷰 품질 (가상 데이터 제외)

- 전체 918건 · 기간 2023-01-31 ~ 2026-11-08
- 중복: 원본 ID 중복 0건 / 같은 날 같은 본문 3건 (후자는 제거하지 않고 표시만)
- 분석 가능한 본문(5자 이상): 823건 (90%)

| 필드 | 확보율 |
|---|---|
| review_date | 100% |
| rating | 22% |
| recommended | 75% |
| app_version | 22% |
| store_country | 25% |
| developer_reply | 2% |
| review_title | 22% |
| playtime_at_review_min | 75% |

**언어 (본문 감지 기준) × 출처 라벨**

| 감지 언어 | 건수 | 분석 가능 | 출처 라벨과 일치 |
|---|---|---|---|
| ko | 349 | 302 | 70% |
| ja | 133 | 129 | 0% |
| en | 402 | 370 | 96% |
| other | 12 | 11 | 0% |
| unknown | 22 | 11 | 0% |

**스토어 × 출처 라벨**

- app_store / —: 200건
- gamerch / bug_report: 32건
- gamerch / chat: 2건
- steam / english: 417건 · 추천 비율 53%
- steam / koreana: 267건 · 추천 비율 89%

## 3. 파일럿 통과 기준 (브리프 10장)

| 항목 | 기준 | 현재 | 판정 |
|---|---|---|---|
| 한국어 리뷰 | 분석 가능 본문 100건 | 302건 | 통과 |
| 일본어 리뷰 | 분석 가능 본문 100건 | 129건 | 통과 |
| 영어 리뷰 | 분석 가능 본문 100건 | 370건 | 통과 |
| 한국(넥슨 커뮤니티) 업데이트 공지 | 3건 | 10건 | 통과 |
| 일본(공식 뉴스) 업데이트 공지 | 3건 | 6건 | 통과 |
| 글로벌(Steam 공지) 업데이트 공지 | 3건 | 49건 | 통과 |
| 출처와 수집 방법 | 모든 레코드 | source_url 100% · method 100% | 통과 |
| 별점(또는 추천)과 날짜 | 90% 이상 | 96% | 통과 |
| 앱 버전 | 확보율 측정 · 결측 허용 | 22% | 측정 완료 |

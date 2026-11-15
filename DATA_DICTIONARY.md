# DATA_DICTIONARY — CSV 열 정의

열 이름과 허용 값의 실제 정의는 `src/schema.py` 한 곳에 있다. 이 문서는 사람용 설명이다.

## 1. 리뷰 (`data/raw/reviews/*.csv`)

| 열 | 필수 | 형식 · 허용 값 | 설명 |
|---|---|---|---|
| review_id | ✅ | `steam_<원본ID>` · `syn_<번호>` | 내부 고유 ID |
| source_review_id | | 문자 | 출처의 원본 ID |
| game_id | ✅ | `blue_archive` | |
| service_region | ✅ | KR / JP / GLOBAL | 운영 권역. Steam = GLOBAL |
| store | ✅ | google_play / app_store / steam | |
| store_country | | ISO 2자리 | Steam은 국가 없음 → 빈 값 |
| language | ✅ | ko / ja / en / other / unknown | **본문 글자로 감지**한 언어 |
| source_language_label | | 출처 값 그대로 | 예: Steam `koreana` |
| review_date | ✅ | YYYY-MM-DD (UTC) | 작성일 |
| collected_at | ✅ | YYYY-MM-DDTHH:MM:SSZ | 수집 시각 |
| rating | | 1~5 또는 빈 값 | 스토어 별점 |
| recommended | | True / False / 빈 값 | Steam 추천 여부. rating과 둘 중 하나는 있어야 함 |
| review_title | | | 앱스토어만 있음 |
| review_text | ✅ | | 원문. 화면에는 200자 이내 발췌만 |
| app_version | | | 결측 허용, 추정 금지 |
| developer_reply | | | |
| votes_up | | 정수 | 도움됨 수 |
| playtime_at_review_min | | 정수(분) | Steam 작성 당시 플레이 시간 |
| source_url | ✅ | URL | 가상은 `synthetic://` |
| collection_method | ✅ | steam_official_api / appfollow_api / appfollow_export / manual_csv / manual_input / synthetic | |
| data_permission_note | ✅ | 문자 | 이용 조건 요약 |
| is_synthetic | ✅ | True / False | 가상 여부. 폴더와 일치해야 함 |

## 2. 업데이트 공지 (`data/raw/updates/*.csv`)

| 열 | 필수 | 형식 | 설명 |
|---|---|---|---|
| update_id | ✅ | `steamnews_<gid>` · `kr_<날짜>_<번호>` | |
| game_id · service_region | ✅ | | |
| update_date | | YYYY-MM-DD | 실제 적용일. 모르면 빈 값 |
| notice_date | ✅ | YYYY-MM-DD | 공지 게시일 |
| version | | | |
| update_type | ✅ | content / character / event / balance / monetization / bugfix / maintenance / system / developer_note / other | Steam 수집분은 사람이 분류하기 전까지 other |
| update_title | ✅ | | |
| update_description | | | 원문 앞 400자 또는 저장 위치 |
| source_url | ✅ | URL | |
| language · collected_at · collection_method · is_synthetic | ✅ | 리뷰와 같음 | |

## 3. 참조 표

- `data/reference/game_registry.csv`: 브리프 6.1 열 + `id_verified_at` · `id_verified_by`(어떻게 확인했나) · `review_access`(수집 가능 상태)
- `data/reference/category_dictionary.csv`: 주제 10개(브리프 7.2) 영문 키 · 세부 주제 · 정의 · 긍정 예 · 부정 예

| 영문 키 | 브리프 주제 |
|---|---|
| character | 캐릭터 및 수집 |
| monetization | BM 및 과금 |
| content_story | 콘텐츠 및 스토리 |
| combat_balance | 전투 및 밸런스 |
| growth_resources | 성장 및 재화 |
| event_ops | 이벤트 및 운영 |
| ui_ux | UI/UX |
| tech_bugs | 기술 및 오류 |
| customer_support | 고객 대응 |
| other | 기타 · 검수 필요 |

## 4. 2주차에 만들 표 (브리프 6.4 · 6.5)

- `review_analysis.csv`: review_id, sentiment, issue_summary, ai_confidence, model_name, prompt_version, analyzed_at, reviewed_by_human
- `review_topics.csv`: review_id, topic, sub_topic, sentiment, evidence, confidence (리뷰 하나에 여러 행)

## 5. 브리프 대비 변경

| 변경 | 이유 |
|---|---|
| `recommended` 추가 | Steam은 별점이 없고 추천/비추천만 있음. rating에 억지로 넣지 않음 |
| `source_language_label` 추가 | 브리프 원칙 "언어는 본문 기준 감지"를 지키면서 출처 라벨과 비교하기 위해 |
| `votes_up` · `playtime_at_review_min` 추가 | Steam이 주는 공개 값. 이탈 직전 장기 이용자 불만 등 해석에 사용 |
| `is_synthetic` 필수 | 가상 · 실제 혼동 방지를 코드로 막기 위해 |
| `store`에 `steam` 추가 | 현재 유일한 허용 리뷰 출처 |
| 업데이트 표에 `collection_method` · `is_synthetic` 추가 | 리뷰와 같은 규칙 적용 |
| 날짜는 UTC | Steam 타임스탬프 기준. 한국 시간 변환은 분석 단계에서 표시 |

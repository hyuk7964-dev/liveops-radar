# DATA_PLAN — 무엇을 어디서 언제 얼마나

## 1. 수집 대상과 현재 확보 상태 (2026-11-08)

| 데이터 | 서비스 권역 | 출처 | 파일럿 목표 | 확보 | 상태 |
|---|---|---|---|---|---|
| 한국어 리뷰 | GLOBAL(PC) | Steam 공식 API | 100~200 | 267 (분석 가능 207) | ✅ 통과 · 단 PC 표본 |
| 영어 리뷰 | GLOBAL(PC) | Steam 공식 API | 100~200 | 417 (분석 가능 370) | ✅ 통과 · 국가 정보 없음 |
| 일본어 리뷰 | JP | AppFollow(미확인) | 100~200 | 0 | ❌ 경로 없음 |
| 한국어 모바일 리뷰 | GLOBAL(KR 스토어) | AppFollow(미확인) | 100~200 | 0 | ⏳ |
| 영어 모바일 리뷰 | GLOBAL(US 스토어) | AppFollow(미확인) | 100~200 | 0 | ⏳ |
| GLOBAL 공지 | GLOBAL | Steam 뉴스 API | 3~5 | 49 | ✅ |
| KR 공지 | GLOBAL(KR) | 넥슨 커뮤니티 수동 입력 | 3~5 | 0 | 👤 |
| JP 공지 | JP | 일본 공식 뉴스 수동 입력 | 3~5 | 0 | 👤 |

수집 기간: 2026-08-10 ~ 2026-11-08(최근 90일). 본 분석 180일은 파일럿 통과 뒤.

## 2. 파일 배치

```
data/
  raw/reviews/steam_global_<언어>_<날짜>.csv     실제 원본. 수정 금지
  raw/updates/updates_global_steam_<날짜>.csv    실제 원본
  raw/updates/updates_kr_manual.csv · updates_jp_manual.csv   사람이 입력
  sample/synthetic_reviews.csv                   가상. 검증 도구 테스트 전용
  reference/game_registry.csv                    앱 ID와 확인 근거
  reference/category_dictionary.csv              주제 10개 정의
  processed/data_collection_log.csv              수집 기록
  processed/game_reviews.csv · review_topics.csv   2주차에 생성
```

## 3. 정제 규칙 (2주차 preprocess에서 구현)

1. 원본 ID(`store` + `source_review_id`)가 같으면 하나만 남긴다.
2. 같은 날 같은 본문은 지우지 않고 `possible_duplicate` 표시만 한다(복붙 밈일 수 있음).
3. 본문 5자 미만 · 빈 본문은 분석에서 빼고 개수를 리포트에 남긴다.
4. 언어는 본문 글자로 다시 감지하고(`language`), 출처 라벨(`source_language_label`)과 다르면 감지값을 쓴다.
5. 원본 파일은 고치지 않는다. 정제 결과는 `processed/`에만 쓴다.

## 4. 업데이트 전후 분석용 구간

- 기본: 공지일 또는 적용일 앞 7일 / 당일 / 뒤 7일. 적용일을 모르면 `notice_date` 기준이라고 표시한다.
- 한 구간 리뷰가 30건 미만이면 14일로 넓히고, 그래도 30건 미만이면 결론을 유보한다.
- 구간 안에 다른 공지(점검 · 이벤트 · 방송)가 있으면 교란 요인으로 같이 표시한다.
- Steam 공지 날짜를 모바일 업데이트 날짜로 쓰지 않는다.

## 5. 1차 관찰 (분석 아님, 표본 설명)

- Steam 최근 90일 추천 비율: 한국어 89%, 영어 53%. 같은 PC판인데 언어 표본 간 차이가 크다. 원인은 아직 모른다(2주차 주제 분류로 확인).
- 개발자 답변 확보율 2%, 앱 버전 0% → 버전 기준 전후 비교는 불가, 날짜 기준만 가능.

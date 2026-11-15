# VALIDATION_PLAN — 데이터 검증과 AI 품질 평가

## 1. 데이터 검증 (구현 완료: `src/validation/validate.py`)

실행: `python -X utf8 -m src.validation.validate` → `docs/data_quality_report.md` 생성. 오류가 하나라도 있으면 종료 코드 1.

| 규칙 | 오류 조건 |
|---|---|
| 필수 열 | `src/schema.py`의 필수 열이 없음 |
| 필수 값 | 필수 열이 빈 값 |
| 허용 값 | service_region · store · language · collection_method · update_type 목록 밖 |
| 날짜 | review_date · notice_date · update_date는 YYYY-MM-DD, collected_at은 ISO UTC |
| ID 중복 | 한 파일 안 review_id · update_id 중복 |
| 별점 | rating이 1~5 밖. rating과 recommended가 둘 다 없음 |
| **실제/가상 분리** | `sample/` 폴더인데 is_synthetic=False, `raw/` 폴더인데 True, collection_method=synthetic과 is_synthetic 불일치 |

리포트 항목: 파일별 오류 수, 기간, 중복(원본 ID · 같은 날 같은 본문), 분석 가능 본문 수, 필드별 확보율, 감지 언어와 출처 라벨 일치율, 파일럿 통과 기준 표(브리프 10장).

검증 도구 자체 테스트: `python -X utf8 tests/test_validate.py` (16개 확인).

## 2. AI 품질 평가 (2주차)

### 정답 데이터셋
- 브리프 기준: 한국어 · 일본어 · 영어 각 50건, 총 150건 사람 라벨.
- **현재 조정안:** 일본어 표본이 없어 한국어 50 · 영어 50으로 시작하고 일본어는 데이터 확보 뒤 추가. 평가 리포트에 이 사실을 적는다.
- 추천/비추천 · 길이 · 날짜가 한쪽으로 쏠리지 않게 층을 나눠 뽑는다(seed 고정).
- 라벨링은 **AI 결과를 보기 전에** 한다. 파일: `data/processed/gold_labels.csv`.
- **일본어 · 영어 라벨은 번역본 기준 (2026-11-10):** 라벨러가 원문을 읽지 못해 `review_text_ko` 칸에 Claude가 직접 번역한 한국어를 넣었다(AI 분류 결과는 보지 않고 원문만 번역). 평가 리포트와 덱 부록에 "ja · en 정답은 번역본을 읽고 단 라벨"이라고 한계로 적는다.

### 1차 결과와 monetization 2차 검수 (2026-11-12)
- 정답 149건(한국어 1건 "안 생겨요"는 의미 없음으로 제외). 리포트 `docs/ai_evaluation_report.md`.
- 감성 Accuracy: ko 0.76 · ja 0.82 · en 0.68 (전체 0.75). 부정 계열(negative + mixed) 여부만 보면 일치율 0.89. 오류 대부분은 mixed와 negative, positive와 neutral 경계.
- 신뢰도 0.8 이상 구간 감성 정답률: ko 0.92 · ja 0.84 · en 0.75.
- **문제:** ja · en monetization Precision 0.47~0.48. 불일치 사례 대부분이 가챠 개편 비판인데 정답이 other · content_story로 달려 있다. 주제 사전은 monetization = "가챠 구조", 예문 "천장이 너무 높다"라서 라벨 기준이 흔들린 것으로 판단.
- **결정(사용자):** 규칙을 먼저 정하고 재검수. 규칙 = **가챠 구조 · 결제 상품 · 과금 정책을 언급하면 monetization을 포함한다**(다른 주제와 함께 달 수 있음).
- **최종 적용 규칙(사용자, 11/12 재검수 후):** 위 규칙보다 좁게 적용했다. **가챠 구조 자체(확률 · 천장 · 픽업)나 가격을 직접 평가할 때만 Y.** 막연한 탐욕 비판("탐욕스러워졌다"), 가챠를 계기로 한 운영 불신, 지나가는 언급, 장르 이름으로서의 "가챠"는 N. 이 좁은 규칙을 공식 규칙으로 한다.
- **v2 결과:** monetization Precision ko 0.83 → 1.00 · ja 0.48 → 0.70 · en 0.47 → 0.68, Recall ko 0.86 · ja 0.89 · en 1.00. 부정 + 과금 정답 수 ja 13 → 17(AI 22) · en 8 → 11(AI 17) · ko 5 → 7(AI 6). 남은 차이는 AI가 넓게 세는 것(탐욕 · 운영 불신)이라 AI 과금 수치는 상한으로 읽는다.
- 처리 기록: 빈칸 1건(appstore_jp_14390490099)은 사용자 메모에 과금 비판이 적혀 있어 Y, 2건(appstore_jp_14723702708 · steam_232596548)은 사용자 확인 후 N → Y.
- 대상은 AI 결과와 무관하게 본문에 가챠 · 과금 단어가 있는 정답 행 49건(ja 24 · en 20 · ko 5). 검수 파일 `data/processed/gold_recheck_monetization.csv`에는 AI 결과를 넣지 않는다. 원래 라벨(v1)은 gold_labels.csv에 그대로 두고, 덱 부록에 v1과 v2를 함께 싣는다.

### 지표
| 영역 | 지표 |
|---|---|
| 감성 | Accuracy, Macro F1 (언어별) |
| 주제 | 주제별 Precision · Recall · F1 (언어별, 리뷰당 다중 주제) |
| 요약 | 원문에 없는 내용 추가 여부(있음/없음) |
| 근거 발췌 | 발췌가 주장을 뒷받침하는가(예/아니오) |
| 전략 제안 | 근거 적합도 · 실행 가능성 사람 평가(1~3) |

### 신뢰도
- `ai_confidence`는 모델이 낸 값이다. 정확도와 섞어 쓰지 않는다.
- 신뢰도 구간별 실제 정확도를 표로 보여 준다(신뢰도가 믿을 만한지 확인).

### 검수 순서
1. 신뢰도 낮은 결과 먼저 2. 원문에 없는 요약 3. 오분류를 `category_dictionary.csv` 정의에 반영 4. `prompt_version` 올리고 재평가 5. 전후 결과 둘 다 보존

## 3. 분석 결과 표시 규칙 (3주차 화면에 강제)

- 모든 수치 옆에 표본 수 `n`, 기간, 출처.
- n < 30이면 "결론 유보" 표시, 비율 막대를 흐리게.
- 업데이트 전후 화면 제목에 "날짜 기준 연관 관찰" 고정. "효과" · "때문에" 문구 금지.
- 원문은 200자 이내 발췌 + 출처 링크.
- 가상 데이터를 불러오면 화면 전체에 "가상 데이터" 표시.

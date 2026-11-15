# IMPLEMENTATION_PLAN — 단계와 체크리스트

브리프 15장 구현 우선순위를 따른다. 각 단계는 "확인 방법"을 통과해야 다음으로 간다.

## 1주차 — 데이터 확보와 분석 가능성 검증

| # | 작업 | 상태 | 확인 방법 · 결과 |
|---|---|---|---|
| 1 | 요구사항 요약 · PRD | ✅ | PRD.md |
| 2 | 출처별 권한 확인 · 체크리스트 | ✅ | DATA_SOURCE_POLICY.md · docs/source_permissions.md |
| 3 | 앱 ID 확인 | ✅ | game_registry.csv (5개 앱, 확인 근거 포함) |
| 4 | 스키마 · 데이터 사전 | ✅ | src/schema.py · DATA_DICTIONARY.md |
| 5 | CSV 검증 · 품질 리포트 도구 | ✅ | tests/test_validate.py 16개 통과 |
| 6 | 가상 샘플(분리) | ✅ | data/sample/ 6행, 검증 통과 |
| 7 | 실제 리뷰 파일럿 (Steam 공식 API) | ✅ | 한국어 267 · 영어 417 |
| 8 | GLOBAL 공지 (Steam 뉴스 API) | ✅ | 49건, update_type 분류는 사람 |
| 9 | KR · JP 공지 수동 입력 | ✅ | KR 7건 · JP 6건 (Claude 브라우저 열람 입력, 사람 확인 대기) |
| 10 | AppFollow 체험 검증 | 👤 | source_permissions.md 9개 질문 |
| 11 | 품질 리포트 | ✅ | docs/data_quality_report.md |

## 결정이 필요한 항목

| ID | 결정 | 선택지 | 추천 |
|---|---|---|---|
| **결정 수정 (2026-11-08, 사용자)** | D2 → 선택지 ②: Apple RSS가 KR 최신 · US 리뷰를 주지 않아 Steam 한국어 · 영어를 한시적으로 메인으로. 모든 화면과 문서에 'PC 글로벌판 표본' 표시. 모바일 KR · US는 AppFollow 등 확보 시 교체 | | |
| **결정 결과 (2026-11-08, 사용자)** | D1 일본어 필수 → 앱스토어 JP(Apple RSS) + Gamerch 커뮤니티 · D2 Steam은 보조 → 메인은 앱스토어 KR · JP · US · AI 실행은 claude -p · 공지는 Claude 브라우저 대행 | | |
| D1 | 일본어 리뷰 | ① AppFollow 체험으로 JP 스토어 확인 ② 일본어를 MVP에서 빼고 "한국어 · 영어 비교"로 축소 ③ Apple RSS 약관 확인 후 사용 | ① 시도, 안 되면 ② |
| D2 | Steam 표본의 위치 | ① 메인 데이터로 쓰고 "PC 글로벌판" 명시 ② 모바일 확보 전 보조로만 | ① (지금 유일한 허용 데이터) |
| D3 | 원문 공개 범위 | 발췌 200자 + 링크 | 현재 정책 유지 |

## 2주차 진행 상황 (2026-11-08)

| # | 작업 | 상태 | 결과 |
|---|---|---|---|
| 1 | 메인 데이터 수집: 앱스토어 RSS | ⚠️ 부분 | JP 100건(2026-08~11) · **KR 100건이나 2023-01~2026-02의 오래된 글** · **US 0건**. 피드가 1~2쪽만 주고 빈 쪽을 자주 돌려줌 |
| 2 | 일본 커뮤니티: Gamerch | ✅ | 불구합 32 · 잡담 2 = 34건(최근 180일). 날짜는 상대 표기 환산(month 정밀도 31건) |
| 3 | 정제 `src/preprocess/clean.py` | ✅ | 918행 → 분석 가능 823 (main 191 · aux 632) |
| 4 | 정답 라벨 표본 `make_gold_sample.py` | ✅ 👤 | 150건(ko · ja는 앱스토어, en은 Steam). **사람 라벨링 대기** |
| 5 | AI 분류 `src/analysis/classify.py` | ✅ | claude -p · claude-sonnet-5-5 · 823건 · 주제 1,117행 · SQLite 캐시. 원문에 없는 근거 1건(오타를 고쳐 인용) |
| 6 | 평가 `src/validation/evaluate.py` | ✅ 도구 | 정답이 채워지면 언어별 감성 F1 · 주제별 F1 · 신뢰도 구간별 정답률 |
| 7 | 업데이트 전후 `src/analysis/update_impact.py` | ✅ 도구 | 같은 날 공지는 한 사건으로 묶음. **모든 사건이 표본 30건 미만으로 결론 유보** |
| 8 | 2차 묶기 `src/analysis/cluster_issues.py` | ✅ | (언어, 주제)별 세부 이슈 → 대표 이슈 4~8개. 예: 영어 과금 부정 126건이 이름 135개로 흩어져 있던 것을 '가챠 개편 반발 43 · 운영사 탐욕 비판 32 · 원복 요구 19 · 50/50 도입 반발 12'로 |
| 9 | 전략 제안 초안 `src/reporting/business_report.py` | ✅ 초안 | docs/business_report_draft.md. 언어별 상위 3주제 x 11칸. 숫자는 코드가 세고 AI는 가설 · 제안만. **정확도 미검증 표시** |
| 11 | 가챠 개편 공지 대조 | ✅ | docs/gacha_revamp_matching.md · 정답지 data/reference/gacha_revamp_timeline.csv. 11/10 적용을 사후 검증 기준일로 |
| 12 | 한국 커뮤니티 정성 메모 | 👤 | 아카 · 디시는 사람이 직접 읽고 기록(11/10 전후 각 20~30건). 양식 · 규칙 준비됨 |
| 10 | D2 수정 반영 | ✅ | Steam 한국어 · 영어 메인 승격, 앱스토어 KR 보조, 정답 표본 150건 재추출(라벨 전이라 영향 없음) |

## 2주차 — AI 분석 엔진 (원래 계획)

1. `src/preprocess/clean.py`: 정제 규칙(DATA_PLAN 3장) → processed/game_reviews.csv
2. 정답 라벨 100건(한국어 50 · 영어 50) 먼저 작성
3. `src/analysis/classify.py`: Anthropic API 배치 분류(감성 · 주제 다중 · 근거 발췌 · 신뢰도), 결과 SQLite 캐시, model_name · prompt_version 기록
4. `src/validation/evaluate.py`: 언어별 F1 → docs/ai_evaluation_report.md
5. `src/analysis/update_impact.py`: 날짜 기준 전후 비교, 표본 부족 시 유보
6. `src/reporting/business_report.py`: 브리프 8.4 11칸 형식

## 2026-11-10 재구성 (1108 멘토 피드백, 결정권자 사용자)

근거: vault `AI-Sessions/wiki/decisions/2026-11-10_LIVEOPS_결과물중심_재구성.md`. 덱 목차: `AI-Sessions/wiki/projects/사업PM-포트폴리오/LIVEOPS_덱목차.md`. 멘토 검토 기한 1주(다음 수업 11/15 예상).

| 순서 | 작업 | 상태 |
|---|---|---|
| 1 | 정답 라벨 150건 | 👤 대기 |
| 2 | 정확도 측정 → 제안 초안 "미검증" 표시 교체 | 라벨 뒤 |
| 3 | 자체 지표 `src/analysis/weighted_metrics.py` (공감 배율 · 장기 이용자 비중) | ✅ 자체 점검 통과 |
| 4 | 덱 15장 (앞 12 결과 · 뒤 3 부록) | 목차 ✅ · 슬라이드 미착수 |
| 5 | 3주차 Streamlit 웹사이트 (유지, 덱에선 부록 증거) | 🟡 첫 버전 app.py (11/14) · 배포 전 |
| 6 | 11/10 전후 14일 비교 (Steam 재수집 + 커뮤니티 메모 post) | 11/24 이후 |
| 7 | 니케 런처 해킹(11/04) · 과거 유사 사례: 커뮤니티 · 유저 반응에 사전 신호가 있었나 | 웹사이트 완성 뒤. 사건 전 구간 기준을 먼저 정하고 볼 것(사후 재구성 편향) |
| 8 | 채널별 다중 에이전트 개념 설계 (부록 2) | 설계만 |

## 3주차 — Streamlit 웹 서비스

Game Overview → AI Review Analysis → Update Impact → 언어 비교 → AI Business Report. VALIDATION_PLAN 3장 표시 규칙을 화면 공통 부품으로.

## 4주차 — 검증 · 배포 · 포트폴리오

오분석 수정, Streamlit Community Cloud 배포(원문 CSV 제외), 시연 영상, PDF, 한계 문서.

## 비용 메모

- Claude Code Max는 개발 도구 비용이다. 배포 서비스의 Anthropic API 호출은 별도 과금 → API 키 · 예산 사용자 확인 필요.
- 분석은 한 번 돌려 SQLite에 저장하고, 화면 조회 때 다시 호출하지 않는다.

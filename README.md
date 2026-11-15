# LIVEOPS RADAR

블루 아카이브 공개 리뷰와 공식 공지로 라이브옵스 이슈를 찾는 AI 포트폴리오. 기준 문서는 `../LIVEOPS_RADAR_PROJECT_BRIEF.md`.

**현재 단계: 1주차 데이터 확보와 분석 가능성 검증** ([IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md))

## 실행

```bash
cd liveops-radar
python -X utf8 tests/test_validate.py                          # 검증 도구 테스트
python -X utf8 -m src.collectors.steam reviews --lang koreana   # Steam 공식 API 리뷰 (english 도 가능)
python -X utf8 -m src.collectors.steam news                     # Steam 공식 공지
python -X utf8 -m src.validation.validate                       # 검증 + docs/data_quality_report.md
```

1주차 코드는 파이썬 표준 라이브러리만 쓴다. API 키가 필요해지면 `.env.example`을 `.env`로 복사해 채운다(.env는 git 제외).

## 문서

| 문서 | 내용 |
|---|---|
| [PRD.md](PRD.md) | 무엇을 만드나 |
| [DATA_PLAN.md](DATA_PLAN.md) | 무엇을 어디서 얼마나, 현재 확보량 |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | CSV 열 정의, 브리프 대비 변경 |
| [DATA_SOURCE_POLICY.md](DATA_SOURCE_POLICY.md) | 출처 이용 원칙과 허용 상태 |
| [VALIDATION_PLAN.md](VALIDATION_PLAN.md) | 데이터 검증 규칙, AI 평가 계획 |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | 단계별 체크리스트, 결정 대기 항목 |
| [docs/source_permissions.md](docs/source_permissions.md) | 출처별 확인 체크리스트(AppFollow 9문항 포함) |
| [docs/data_quality_report.md](docs/data_quality_report.md) | 자동 생성 품질 리포트 |

## 데이터 구분

- `data/raw/` 실제 수집 원본(수정 금지) · `data/sample/` 가상 데이터(테스트 전용) · `data/processed/` 가공 결과
- 원문 리뷰 CSV는 공개 배포에 포함하지 않는다.

## 웹사이트 (Streamlit)

```bash
python -X utf8 -m src.reporting.public_data      # 원문에서 200자 발췌본 만들기 → data/public/
python -X utf8 -m streamlit run app.py           # http://localhost:8501
python -X utf8 tests/test_app.py                 # 앱 오류 없음 · 온도 65도 · 발췌만 읽는지
```

앱은 `data/public/`(발췌 + 링크) · `data/processed/`의 집계 결과(weighted_metrics · update_impact · issue_groups) · `data/reference/` · `docs/`만 읽는다. 원문 리뷰 CSV는 읽지 않는다.

### 배포 (Streamlit Community Cloud) — 아직 안 함

1. `python -X utf8 -m src.reporting.public_data` 로 `data/public/`를 최신으로 만든다.
2. 이 폴더(`liveops-radar/`)만 담은 새 GitHub 저장소를 만든다. `.gitignore`가 원문(`data/raw/reviews/`, `processed/game_reviews.csv`, `gold_*.csv`, `review_topics.csv`, `analysis.sqlite`)과 `.env`를 뺀다. 푸시 전에 `git status`로 원문 파일이 목록에 없는지 확인한다.
3. share.streamlit.io → Create app → 저장소 · 브랜치 `main` · Main file `app.py` → Deploy. 의존성은 `requirements.txt`를 읽는다(앱은 API 키가 필요 없어 Secrets 비워 둠).
4. 배포 주소를 덱 부록 1과 이력서 링크에 넣는다. 데이터를 바꾸면 1번을 다시 하고 푸시하면 자동 재배포된다.

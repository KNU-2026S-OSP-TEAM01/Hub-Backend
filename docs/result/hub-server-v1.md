# Hub Server v1 구현 결과

> 작성일: 2026-05-19
> 브랜치: `feat/hub-implement`
> 참고: `docs/hub-analysis.md`, `docs/plan/hub-server-implementation-plan.md`

---

## 구현 범위

PLS DB의 `parking_lots` 테이블을 읽기 전용으로 참조해 일반 사용자에게 주차장 현황을 제공하는 공개 API 서버.

---

## 주요 설계 결정

### 1. PLS DB 직접 참조 (DB 공유)

Hub와 PLS가 동일한 PostgreSQL 인스턴스를 바라본다. Hub → PLS HTTP 통신 없음, 폴링 없음.
`available_spaces`는 PLS가 입출차 처리 시 실시간으로 갱신하므로 Hub가 읽으면 항상 최신값이다.

### 2. ORM 모델에 필요한 컬럼만 선언

`owner_user_id`, `api_key`는 Hub 모델에 선언하지 않는다. SQLAlchemy는 선언된 컬럼만 SELECT하므로 민감 필드가 네트워크 구간에서부터 전달되지 않는다.

이 방식의 부수 효과로 테스트 독립성도 확보된다. `create_all`이 Hub 모델 기준으로 단순한 `parking_lots` 테이블을 생성하므로 PLS의 `users` 테이블이나 FK 제약 없이 독립적으로 테스트할 수 있다.

### 3. Hub 자체 DB 없음

공영주차장 등 추가 기능 이전까지 Hub는 자체 테이블을 생성하지 않는다. Alembic 마이그레이션 불필요.

---

## 프로젝트 구조

```
hub-backend/
├── app/
│   ├── main.py          # FastAPI 앱, CORS 미들웨어
│   ├── config.py        # 환경변수 (DATABASE_URL, FRONTEND_URL)
│   ├── database.py      # SQLAlchemy 엔진, get_db
│   ├── models/
│   │   └── parking_lot.py   # 읽기 전용 ORM 모델
│   ├── schemas/
│   │   └── lot.py           # LotOut 응답 스키마
│   └── routers/
│       └── lots.py          # GET /api/v1/lots, GET /api/v1/lots/{lot_id}
└── tests/
    ├── conftest.py          # 테스트 DB, client, lot 픽스처
    └── routers/
        └── test_lots.py     # 8개 테스트
```

---

## API

| Method | Path | 인증 | 설명 |
|--------|------|------|------|
| GET | `/api/v1/lots` | 없음 | 주차장 목록 |
| GET | `/api/v1/lots/{lot_id}` | 없음 | 주차장 단건 |

응답에서 제외되는 필드: `owner_user_id`, `api_key`

---

## 인프라

| 항목 | 내용 |
|------|------|
| 앱 포트 | 8001 |
| 운영 DB | PLS DB (호스트 포트 `5432` 경유, `host.docker.internal:5432`) |
| 테스트 DB | Hub 전용 PostgreSQL (`localhost:5434`) |
| Linux Docker | `extra_hosts: host.docker.internal:host-gateway` 필요 |

---

## 테스트 결과

```
8 passed, coverage 86%
```

| 테스트 | 검증 내용 |
|--------|----------|
| `test_list_lots_returns_lot` | 목록에 주차장 반환 |
| `test_list_lots_excludes_sensitive_fields` | `owner_user_id`, `api_key` 미포함 확인 |
| `test_list_lots_returns_empty_when_no_lots` | 데이터 없을 때 빈 배열 반환 |
| `test_list_lots_returns_correct_fields` | 필드 값 정확성 |
| `test_get_lot_returns_lot` | 단건 조회 정상 |
| `test_get_lot_excludes_sensitive_fields` | 단건에서도 민감 필드 미포함 확인 |
| `test_get_lot_not_found` | 존재하지 않는 ID → 404 |
| `test_get_lot_daily_max_fee_none` | `daily_max_fee` null 처리 |

---

## 미결 사항

| 항목 | 내용 |
|------|------|
| 수동 연동 확인 | `docs/ref/integration-test-guide.md` 참고 |
---

## 남은 미결 사항

| 항목 | 내용 |
|------|------|
| 위도·경도 | 지오코딩 API 연동 후 PLS 스키마 변경과 함께 구현 |
| 공영주차장 | 공공 API 실시간 호출 → 필요한 필드만 파싱해서 PLS 데이터와 합쳐 반환 |
| FE Hub API 명세 | FE팀 요구사항 확정 후 추가 엔드포인트 협의 |
| CORS | Hub FE URL이 정해지면 `FRONTEND_URL` 환경변수로 추가 |

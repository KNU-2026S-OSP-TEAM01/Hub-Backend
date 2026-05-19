# Hub Server 구현 계획

> 작성일: 2026-05-19
> 참고 문서: `docs/hub-analysis.md`

---

## 구현 범위

- PLS DB의 `parking_lots` 테이블을 읽기 전용으로 참조
- 일반 사용자용 공개 API 2개 제공

---

## 엔티티

### `ParkingLot` (읽기 전용)

PLS의 `parking_lots` 테이블에 매핑하되, **Hub가 사용하는 컬럼만 선언**한다.

`owner_user_id`, `api_key`는 모델에 선언하지 않는다. SQLAlchemy는 모델에 선언된 컬럼만 SELECT하므로 PLS DB에 쿼리할 때 민감 필드를 아예 건드리지 않는다. 테스트 시 `create_all`로 단순 테이블을 생성할 때도 FK(`users` 테이블 참조) 없이 독립적으로 동작한다.

| 컬럼 | 타입 | 모델 선언 |
|------|------|---------|
| `id` | UUID | ✅ |
| `owner_user_id` | UUID | ❌ (선언 안 함) |
| `name` | VARCHAR(100) | ✅ |
| `address` | VARCHAR(255) | ✅ |
| `total_spaces` | INT | ✅ |
| `available_spaces` | INT | ✅ |
| `base_fee` | INT | ✅ |
| `base_duration_minutes` | INT | ✅ |
| `extra_fee_per_unit` | INT | ✅ |
| `extra_fee_unit_minutes` | INT | ✅ |
| `daily_max_fee` | INT \| NULL | ✅ |
| `api_key` | VARCHAR(64) | ❌ (선언 안 함) |
| `created_at` | TIMESTAMPTZ | ✅ |
| `updated_at` | TIMESTAMPTZ | ✅ |

---

## API

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/lots` | 주차장 목록 |
| GET | `/api/v1/lots/{lot_id}` | 주차장 단건 |

### `GET /api/v1/lots`

인증 없음. `owner_user_id`, `api_key` 제외하고 반환.

**응답 `200 OK`**

```json
[
  {
    "id": "uuid",
    "name": "본관 주차장",
    "address": "경북대학교 북문 앞",
    "total_spaces": 100,
    "available_spaces": 73,
    "base_fee": 1000,
    "base_duration_minutes": 30,
    "extra_fee_per_unit": 200,
    "extra_fee_unit_minutes": 10,
    "daily_max_fee": 10000,
    "created_at": "2026-05-19T10:00:00+09:00",
    "updated_at": "2026-05-19T10:00:00+09:00"
  }
]
```

### `GET /api/v1/lots/{lot_id}`

인증 없음. `owner_user_id`, `api_key` 제외.

**응답 `200 OK`**

```json
{
  "id": "uuid",
  "name": "본관 주차장",
  "address": "경북대학교 북문 앞",
  "total_spaces": 100,
  "available_spaces": 73,
  "base_fee": 1000,
  "base_duration_minutes": 30,
  "extra_fee_per_unit": 200,
  "extra_fee_unit_minutes": 10,
  "daily_max_fee": 10000,
  "created_at": "2026-05-19T10:00:00+09:00",
  "updated_at": "2026-05-19T10:00:00+09:00"
}
```

**에러**

| 상태 | detail | 원인 |
|------|--------|------|
| 404 | `lot_not_found` | 존재하지 않는 주차장 |

---

## 환경변수

`.env`는 로컬 직접 실행 기준으로 작성한다. Docker 컨테이너 실행 시에는 `docker-compose.yml`의 `environment`로 override한다.

**`.env` (로컬 직접 실행용)**

```env
DATABASE_URL=postgresql+asyncpg://openpark:openpark@localhost:5432/openpark
TEST_DATABASE_URL=postgresql+asyncpg://openpark:openpark@localhost:5434/openpark_hub_test
```

> 테스트(`pytest`)는 항상 로컬에서 실행하므로 `TEST_DATABASE_URL`은 `localhost:5434` 고정이다.

---

## 프로젝트 구조

PLS와 동일한 구조를 따른다.

```
hub-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── parking_lot.py   # 읽기 전용 ORM 모델
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── lot.py           # LotOut (응답 스키마)
│   └── routers/
│       ├── __init__.py
│       └── lots.py          # GET /api/v1/lots, GET /api/v1/lots/{lot_id}
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── routers/
│       ├── __init__.py
│       └── test_lots.py
├── .env
├── .env.example
├── docker-compose.yml       # Hub 앱 + 테스트 DB
├── Dockerfile
├── pytest.ini
└── requirements.txt
```

---

## Docker Compose

Hub 앱과 테스트 DB를 하나의 compose 파일로 관리한다.
운영 DB(PLS)는 호스트 포트(`5432`)를 통해 접근한다.

```yaml
services:
  hub:
    build: .
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql+asyncpg://openpark:openpark@host.docker.internal:5432/openpark
    extra_hosts:
      - "host.docker.internal:host-gateway"   # Linux 대응

  db_test:
    image: postgres:16
    environment:
      POSTGRES_DB: openpark_hub_test
      POSTGRES_USER: openpark
      POSTGRES_PASSWORD: openpark
    ports:
      - "5434:5432"                            # PLS 테스트 DB(5433)와 충돌 방지
```

`hub` 서비스의 `DATABASE_URL`은 `docker-compose.yml`에서 직접 지정해 `.env`의 로컬 값을 override한다.

---

## Dockerfile

uvicorn을 포트 8001로 명시한다.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

## requirements.txt

Hub는 JWT, 암호화, DB 마이그레이션이 불필요하므로 PLS보다 의존성이 적다.

```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
pydantic-settings

# test
pytest
pytest-asyncio
pytest-cov
httpx
```

---

## pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts =
    --cov=app
    --cov-report=term-missing
    --cov-fail-under=60
```

---

## 구현 순서

| 단계 | 작업 | 비고 |
|------|------|------|
| 1 | 프로젝트 세팅 | requirements.txt, Dockerfile, docker-compose.yml, pytest.ini |
| 2 | `config.py`, `database.py` | PLS 코드 참고 |
| 3 | `models/parking_lot.py` | PLS 테이블 읽기 전용 매핑 |
| 4 | `schemas/lot.py` | `LotOut` — 민감 필드 제외 |
| 5 | `routers/lots.py` | `GET /api/v1/lots`, `GET /api/v1/lots/{lot_id}` |
| 6 | `main.py` | 라우터 등록, CORS 설정 |
| 7 | 테스트 작성 및 실행 | `docker compose up db_test -d` 후 `pytest` |
| 8 | 수동 연동 확인 | PLS compose 실행 후 Hub 로컬 기동, `GET localhost:8001/api/v1/lots` 응답 확인 |

---

## 미결 사항

| 항목 | 내용 |
|------|------|
| 위도·경도 | 지오코딩 API 연동 후 PLS 스키마 변경과 함께 구현 |
| 공영주차장 | 공공 API 실시간 호출 → 필요한 필드만 파싱해서 PLS 데이터와 합쳐 반환. Hub 자체 DB 불필요. PLS 연결 확인 후 진행. |
| FE Hub API 명세 | FE팀 요구사항 확정 후 추가 엔드포인트 협의 |
| CORS | Hub FE URL이 정해지면 `FRONTEND_URL` 환경변수로 추가 |

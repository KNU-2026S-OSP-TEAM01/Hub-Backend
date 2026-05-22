# Hub ↔ PLS 로컬 연동 테스트 가이드

> 작성일: 2026-05-19

Hub가 실제 PLS DB에서 데이터를 읽어오는지 확인하는 수동 연동 테스트 절차.

---

## 사전 요구사항

- Docker Desktop 실행 중
- 두 리포지토리가 로컬에 클론되어 있음
- 각 리포지토리에 Python 가상환경(`.venv`) 구성 완료

```
OSP_prj/
├── Parking-Lot-Backend/   # PLS
└── Hub-Backend/           # Hub
```

---

## 전체 흐름

```
[Parking-Lot-Backend/]          [Hub-Backend/]
  docker compose up db app         docker compose up hub
         │                                  │
    PostgreSQL :5432              host.docker.internal:5432
         │                                  │
    PLS 앱 :8000              ←── DB 공유 ──→ Hub 앱 :8001
         │
  seed_integration.py
  (더미 데이터 주입)
```

---

## 단계별 절차

### Step 1 — PLS DB와 앱 기동

`Parking-Lot-Backend/` 디렉토리에서 실행한다.

```bash
docker compose up db app -d
```

`db`(PostgreSQL :5432)와 `app`(PLS :8000) 두 서비스가 실행된다.
`db_test`(:5433)는 PLS 유닛 테스트 전용이므로 생략해도 된다.

컨테이너 상태 확인:

```bash
docker compose ps
```

---

### Step 2 — PLS DB 마이그레이션

`Parking-Lot-Backend/` 디렉토리에서 가상환경을 활성화하고 실행한다.

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

alembic upgrade head
```

정상 완료 시 출력 예시:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 6361c625a6af, init redesigned schema
INFO  [alembic.runtime.migration] Running upgrade 6361c625a6af -> ca3ed5b9fa78, drop is_active
```

> DB 컨테이너가 완전히 준비되기 전에 실행하면 연결 오류가 날 수 있다. 잠시 후 재시도하면 된다.

---

### Step 3 — 더미 데이터 주입

`Parking-Lot-Backend/` 디렉토리에서 가상환경이 활성화된 상태로 실행한다.

```bash
python scripts/seed_integration.py
```

스크립트가 수행하는 작업:

1. `POST /api/v1/signup` — 테스트 계정 생성 (`testowner`)
2. `POST /api/v1/login` — JWT 토큰 발급
3. `POST /api/v1/lots` × 2 — 주차장 2개 생성

정상 완료 시 출력 예시:

```
▶ 회원가입 중...
  ✔ 계정 생성: testowner
▶ 로그인 중...
  ✔ 토큰 발급 완료
▶ 주차장 생성 중...
  ✔ [북문 주차장] id=xxxxxxxx-... api_key=abcd1234...
  ✔ [남문 주차장] id=yyyyyyyy-... api_key=efgh5678...

완료. Hub 컨테이너 기동 후 연동을 확인하세요.
```

스크립트는 이미 계정이 존재하면 로그인으로 넘어가므로 **재실행해도 안전**하다.

---

### Step 4 — Hub 컨테이너 기동

`Hub-Backend/` 디렉토리에서 실행한다.

```bash
docker compose up hub -d
```

Hub 컨테이너는 `host.docker.internal:5432`로 PLS DB에 접근한다.

> **Linux에서는** `docker-compose.yml`에 `extra_hosts: - "host.docker.internal:host-gateway"`가 선언되어 있어야 한다. 현재 파일에 이미 포함되어 있다.

컨테이너 로그 확인:

```bash
docker compose logs hub
```

정상 기동 시:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

### Step 5 — 연동 확인

**목록 조회**

```bash
curl http://localhost:8001/api/v1/lots
```

예상 응답:

```json
[
  {
    "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "name": "북문 주차장",
    "address": "경북대학교 북문 앞",
    "total_spaces": 100,
    "available_spaces": 100,
    "base_fee": 1000,
    "base_duration_minutes": 30,
    "extra_fee_per_unit": 200,
    "extra_fee_unit_minutes": 10,
    "daily_max_fee": 10000,
    "created_at": "...",
    "updated_at": "..."
  },
  {
    "id": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "name": "남문 주차장",
    ...
    "daily_max_fee": null
  }
]
```

**확인 포인트**

| 항목 | 기대값 |
|------|--------|
| 주차장 2개 반환 | ✅ |
| `owner_user_id` 없음 | ✅ |
| `api_key` 없음 | ✅ |
| `daily_max_fee: null` 정상 처리 | ✅ |

**단건 조회**

목록 응답에서 `id`를 복사해 확인한다.

```bash
curl http://localhost:8001/api/v1/lots/{id}
```

**존재하지 않는 ID 조회**

```bash
curl http://localhost:8001/api/v1/lots/00000000-0000-0000-0000-000000000000
# 응답: {"detail": "lot_not_found"} 404
```

---

## 트러블슈팅

**`alembic upgrade head` 연결 오류**

DB 컨테이너가 아직 준비 중일 수 있다. 5초 후 재시도한다.

**Hub 응답이 빈 배열 `[]`**

- Step 3 더미 데이터 주입이 성공했는지 확인
- Hub `docker-compose.yml`의 `DATABASE_URL`이 `host.docker.internal:5432`인지 확인
- `docker compose logs hub`에서 DB 연결 오류 여부 확인

**Hub 컨테이너가 DB 연결 실패**

Linux 환경에서 `host.docker.internal`을 못 찾는 경우다. `docker-compose.yml`에 아래가 있는지 확인한다.

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

---

## 정리

테스트 후 컨테이너를 종료한다.

```bash
# Hub-Backend/
docker compose down

# Parking-Lot-Backend/
docker compose down
```

DB 볼륨까지 초기화하려면:

```bash
# Parking-Lot-Backend/
docker compose down -v
```

# Hub Server 요구사항 분석

> 작성일: 2026-05-15
> 참고 문서:
> - `PLS/docs/result/fe-feedback-apply-v2.md` — 아키텍처 전환 결정
> - `PLS/docs/ref/fe-api-reference.md` — FE팀 API 명세

---

## 1. 현재 아키텍처 (확정)

### DB 공유 방식

```
Docker 내부망
┌──────────────────────────────────────────────────┐
│  pls          ──┐                                │
│  hub          ──┼──► db (postgres, 공유)          │
└──────────────────────────────────────────────────┘
```

- Hub와 PLS가 **동일한 PostgreSQL 컨테이너**를 바라본다.
- Hub는 PLS의 `parking_lots` 테이블을 직접 SELECT한다.
- PLS → Hub HTTP 통신 없음. Hub → PLS 폴링 없음.

### 컨테이너 간 네트워크 접근

Hub와 PLS는 **별도 Docker Compose**로 실행되므로 기본적으로 서로 다른 네트워크에 속한다.
`localhost`로는 서로를 참조할 수 없으며, DB 공유를 위해 아래 두 방법 중 하나를 선택해야 한다.

---

#### 방법 1 — Docker 외부 네트워크 공유 (권장)

미리 공용 네트워크를 만들고, 두 Compose가 모두 참여한다.

```bash
# 최초 1회 생성
docker network create openpark-net
```

PLS `docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:16
    networks:
      - openpark-net
    # ... 나머지 설정

networks:
  openpark-net:
    external: true
```

Hub `docker-compose.yml`:
```yaml
services:
  hub:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://openpark:openpark@db/openpark
    networks:
      - openpark-net

networks:
  openpark-net:
    external: true
```

같은 네트워크에 있으므로 Hub에서 `db`라는 서비스 이름으로 PLS의 DB에 접근할 수 있다.

---

#### 방법 2 — 호스트 포트로 접근 (단순하지만 DB가 호스트에 노출됨)

PLS compose가 이미 DB 포트를 호스트에 노출하고 있다(`5432:5432`).
Hub 컨테이너에서 `host.docker.internal`(Windows/Mac) 또는 호스트 IP로 접근한다.

Hub `docker-compose.yml`:
```yaml
services:
  hub:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://openpark:openpark@host.docker.internal:5432/openpark
```

| 접근 주체 | 대상 | 주소 |
|----------|------|------|
| Hub 컨테이너 | PLS DB | `host.docker.internal:5432` |
| 호스트(개발자) | PLS | `localhost:8000` |
| 호스트(개발자) | Hub | `localhost:8001` |

---

## 2. Hub Server의 역할

일반 사용자(주차장을 이용하려는 사람)에게 **주차장 현황을 조회**하는 공개 API를 제공한다.

| 서버 | 대상 | 주요 기능 |
|------|------|----------|
| PLS | 주차장 소유자 | 주차장 등록·수정·삭제, 입출차 처리, 로그 조회 |
| Hub | 일반 사용자 | 주차장 목록/현황 조회 |

---

## 3. Hub가 읽는 PLS DB 테이블

Hub는 PLS DB의 `parking_lots` 테이블을 읽기 전용으로 사용한다.

### `parking_lots` 테이블 구조 (PLS 정의)

| 컬럼 | 타입 | Hub 노출 여부 | 비고 |
|------|------|-------------|------|
| `id` | UUID | ✅ | 주차장 식별자 |
| `owner_user_id` | UUID | ❌ | 민감 정보 — 노출 금지 |
| `name` | VARCHAR(100) | ✅ | |
| `address` | VARCHAR(255) | ✅ | |
| `total_spaces` | INT | ✅ | |
| `available_spaces` | INT | ✅ | 실시간 반영 (PLS가 입출차 시 갱신) |
| `base_fee` | INT | ✅ | |
| `base_duration_minutes` | INT | ✅ | |
| `extra_fee_per_unit` | INT | ✅ | |
| `extra_fee_unit_minutes` | INT | ✅ | |
| `daily_max_fee` | INT \| NULL | ✅ | |
| `api_key` | VARCHAR(64) | ❌ | 민감 정보 — 노출 금지 |
| `created_at` | TIMESTAMPTZ | ✅ | |
| `updated_at` | TIMESTAMPTZ | ✅ | |

`available_spaces`는 PLS가 입출차 처리 시 실시간으로 갱신하므로 Hub가 읽으면 항상 최신값이다.

---

## 4. Hub가 구현할 기능

### 4-1. 공개 API (인증 없음)

일반 사용자는 로그인 없이 주차장 현황을 조회할 수 있어야 한다.

#### `GET /api/v1/lots` — 주차장 목록 조회

- `owner_user_id`, `api_key` 제외하고 반환

**응답 예시**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "본관 주차장",
    "address": "경북대학교 북문 앞",
    "total_spaces": 100,
    "available_spaces": 73,
    "base_fee": 1000,
    "base_duration_minutes": 30,
    "extra_fee_per_unit": 200,
    "extra_fee_unit_minutes": 10,
    "daily_max_fee": 10000,
    "updated_at": "2026-05-15T10:00:00+09:00"
  }
]
```

#### `GET /api/v1/lots/{lot_id}` — 주차장 단건 조회

- `owner_user_id`, `api_key` 제외

**에러**

| 상태 | detail | 원인 |
|------|--------|------|
| 404 | `lot_not_found` | 존재하지 않는 주차장 |

---

### 4-2. 검토 필요 기능 (FE팀과 협의)

| 기능 | 설명 | 비고 |
|------|------|------|
| 검색 (이름/주소) | 키워드로 주차장 검색 | ILIKE 쿼리로 구현 가능 |
| 만석 필터 | `available_spaces > 0`만 표시 | 쿼리 파라미터로 제어 가능 |
| 위치 기반 정렬 | 위도·경도 기준 가까운 순 정렬 | `parking_lots`에 좌표 컬럼 없음 → PLS 스키마 변경 필요 |
| 요금 계산 미리보기 | 예상 주차 시간 입력 → 요금 계산 | PLS의 `fee.py` 로직 포팅 가능 |

---

## 5. 기술 스택 (PLS와 동일 권장)

| 항목 | 기술 |
|------|------|
| 언어/프레임워크 | Python 3.12 / FastAPI |
| DB 접근 | SQLAlchemy 2.x (asyncio) + asyncpg |
| 마이그레이션 | 없음 (PLS 테이블을 읽기만 함, DDL 소유권은 PLS) |
| 환경변수 | pydantic-settings |
| 테스트 | pytest, pytest-asyncio, httpx |
| 인프라 | Docker Compose (PLS의 `db` 서비스 공유) |

Hub는 별도 테이블을 생성하지 않으므로 Alembic 마이그레이션이 불필요하다.

---

## 6. 환경변수

```env
# 방법 1 — 외부 네트워크 공유 시 (서비스명 'db'로 접근)
DATABASE_URL=postgresql+asyncpg://openpark:openpark@db/openpark

# 방법 2 — 호스트 포트로 접근 시
DATABASE_URL=postgresql+asyncpg://openpark:openpark@host.docker.internal:5432/openpark

# 로컬 직접 실행 시 (Docker 없이)
DATABASE_URL=postgresql+asyncpg://openpark:openpark@localhost/openpark
```

---

## 7. Docker Compose 구성

Hub와 PLS는 각자의 `docker-compose.yml`로 실행된다. 상세 내용은 섹션 1의 네트워크 접근 방법 참고.

---

## 8. 구현 순서

| 단계 | 작업 |
|------|------|
| 1 | 프로젝트 세팅 (FastAPI, requirements.txt, Dockerfile) |
| 2 | DB 연결 설정 — PLS `parking_lots` 모델을 읽기 전용으로 참조 |
| 3 | `GET /api/v1/lots` 구현 |
| 4 | `GET /api/v1/lots/{lot_id}` 구현 |
| 5 | Docker Compose 연동 확인 |
| 6 | PLS와 로컬 연동 테스트 |

---

## 9. 미결 사항

| 항목 | 내용 |
|------|------|
| FE Hub API 명세 | FE팀 요구사항 미확정. 최소 `GET /api/v1/lots`, `GET /api/v1/lots/{lot_id}` 구현 후 협의 |
| 위치 정보 | `parking_lots` 테이블에 위도·경도 컬럼 없음. 필요 시 PLS 스키마 변경 필요 |
| Hub 인증 | 현재 인증 불필요(공개 API). 향후 즐겨찾기 등 사용자 기능 추가 시 재검토 |

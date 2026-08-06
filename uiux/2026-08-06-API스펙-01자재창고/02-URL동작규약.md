# 01 자재창고 — URL·동작 규약

> 작성일: 2026-08-06 (v0.1) · 작성 주체: CREFLE OMF 팀 (UI/UX)
> `00-설계.md` §6 실행 순서 **2단계**. 신설 패턴 3종(라·마·바)의 **URL 모양과 동작**을 정하고, 1단계가 남긴 확인 3건을 닫는다.

---

## 1. 계승 — 기준정보에서 그대로

| 규약 | |
| --- | --- |
| **네임스페이스 = 물리 모델 스키마** | `/logistics/*` · `/inventory/*` · `/trace/*` |
| **`/lookup` 을 두지 않는다** | 조회 전용도 같은 경로에 GET만. 나중에 화면이 생기면 POST를 더한다 |
| **명시적 오퍼레이션은 `:동사`** | PATCH에 여러 의미를 싣지 않는다 |
| **`/history` 를 두지 않는다** | 변경 이력은 횡단 `GET /audit/events` 하나 (#68 해소 전까지) |

⚠ **파일과 네임스페이스는 다른 축이다.** `putaway_rule` 은 스키마가 `logistics` 라 경로가 `/logistics/putaway-rules` 이지만, **성격이 마스터**라 파일은 `mdm-기준정보.json` 이다(§5 확인 1).

---

## 2. **라. 업무 문서 형** — 27테이블 중 15리소스

```
GET    /logistics/goods-receipts                  목록 — ⚠ 기간 필터 필수
GET    /logistics/goods-receipts/{id}             헤더 + 라인
POST   /logistics/goods-receipts                  생성 (작성중)
PUT    /logistics/goods-receipts/{id}             헤더 수정 — 작성중만 · 낙관적 잠금
PUT    /logistics/goods-receipts/{id}/lines       라인 전체 치환
POST   /logistics/goods-receipts/{id}:confirm     확정
POST   /logistics/goods-receipts/{id}:post        전기 → 원장
POST   /logistics/goods-receipts/{id}:cancel      취소
```

### 2-1. 마스터 형과 갈리는 네 곳

| | 마스터 형 | **업무 문서 형** |
| --- | --- | --- |
| 끄기 | `:deactivate` | ⛔ **없다** — `:cancel`(취소 **상태**로 전이) |
| 목록 | 전건 | ⚠ **기간 필터 필수** — 전표는 쌓인다(L-3) |
| 수정 | 언제나 | **작성중 상태에서만.** 확정 후 수정은 `400 STATE_LOCKED`(G-1) |
| 이력 | `/history` | 횡단 `/audit/events` |

### 2-2. ⭐ 상태 전이 동사를 **넷으로 통일한다** *(1단계 확인 1 — 닫음)*

문서마다 업무 용어가 다르다(「입고 처리」·「실사 마감」·「조정 전기」). **업무 용어가 아니라 전이의 성격으로 이름을 정한다.**

| 동사 | 뜻 | 언제 |
| --- | --- | --- |
| **`:confirm`** | **문서가 확정된다** — 더 못 고친다 | 작성중 → 확정 |
| **`:post`** | **원장에 기록된다** — 재고가 움직인다 | 확정 → 전기 |
| **`:cancel`** | 취소 상태로 전이 | 어느 상태에서든(문서별 허용 범위는 다르다) |
| **`:request-approval`** | 승인 요청 | 횡단 — `app-공통` 소관 |

**⭐ `:confirm` 과 `:post` 를 나누는 이유** — 「확정했는데 전기가 실패」를 표현할 수 있다. B-8(트랜잭션 경계)이 **외부 호출을 트랜잭션 밖**에 두므로 두 순간이 갈릴 수 있다.

> **규칙**: **화면이 두 버튼으로 나눠 놓았으면 두 오퍼레이션, 한 버튼이면 하나.** 임의로 쪼개지 않는다.
>
> - `W-01-12` 재고조정 — 「조정 상신 → 승인 → **전기**」 · **셋이 다 다르다** → `:request-approval` · (승인은 횡단) · `:post`
> - `W-01-10` 정상품 입하 처리 — 「입고 처리」 **한 버튼** → `:post` 하나 (확정과 전기가 같은 순간)

**문서 고유 행위는 고유 동사를 쓴다** — `:split`(`W-01-03` 초과 분리) · `:depart`/`:arrive`(`M-01-10` 이동) · `:complete`(`M-01-05` 적치).

### 2-3. `goods_issue` — 경로를 나누지 않는다 *(1단계 확인 3 — 닫음)*

**실측: `issue_type_code` 가 있다**(`app.code_t NOT NULL`). `source_document_type_code`·`destination_type_code`·`reason_code` 도 함께 있다.

```
POST /logistics/goods-issues        { issueTypeCode: "일반출고" | "반품" | "기타출고", ... }
```

세 화면(`M-01-08` 출고 · `W-01-05` 반품 · `W-01-06` 기타출고)이 **같은 경로에 다른 유형**을 보낸다. 경로를 나누면 **같은 전표가 세 벌로 갈라지고 조회가 세 곳을 봐야** 한다.

⚠ **값 목록 미정** — G-2 적용, `enum` 을 못박지 않는다.

### 2-4. `stock_transfer` — **한 문서 + 두 전이** *(1단계 확인 — 닫음)*

**실측이 답을 준다** — `shipped_at` · `received_at` 이 **한 행에 둘 다** 있다.

```
POST /logistics/stock-transfers               생성
POST /logistics/stock-transfers/{id}:depart   반출 스캔  → shipped_at
POST /logistics/stock-transfers/{id}:arrive   도착 스캔  → received_at
GET  /logistics/stock-transfers?status=미완   이어하기 목록
```

배지단말 **#8**(통신 두절 시 입·출측을 단일 단말로)이 **한 단말이 양쪽을 다 한다**고 했으므로 두 문서로 나누면 그 규칙이 깨진다.

---

## 3. **마. 원장 형** — `inventory_transaction`

```
GET /inventory/transactions?businessDateFrom=&businessDateTo=      ⚠ 기간 필수
GET /inventory/transactions/{businessDate}/{transactionId}          ⚠ 복합 키
⛔ POST · PUT · DELETE  없음
```

### 3-1. ⚠ 복합 키가 URL 에 드러난다

```
PRIMARY KEY (inventory_transaction_id, business_date)
```

**`id` 만으로는 행을 못 찾는다** — 파티션 키가 없으면 전 파티션을 스캔한다. 셋 중 하나여야 하는데:

| 안 | 판정 |
| :-: | --- |
| `/transactions/{id}` | ⛔ 전 파티션 스캔 |
| `/transactions/{id}?businessDate=` | ⚠ 필수 쿼리는 경로 식별자로서 어색하다 |
| **`/transactions/{businessDate}/{id}`** | ✅ **채택** — 복합 키를 있는 그대로 |

### 3-2. 쓰기 경로를 두지 않는다

**전표의 `:post` 가 만든다.** 화면이 원장을 직접 쓰면 「어느 전표에서 왔는가」(`source_document_type_code`·`source_document_id`)가 비어 추적이 끊긴다.

**취소도 없다** — `reversal_of_transaction_id` + `reversal_of_business_date` 로 **역처리 행을 추가**한다. 그 행을 만드는 것도 전표의 `:cancel` 이다.

---

## 4. **바. 파생 잔액 형** — `inventory_balance`

```
GET /inventory/balances?groupBy=item|lot|location&warehouseId=&itemId=&lotId=
⛔ 쓰기 없음
```

### 4-1. 11축이 곧 쿼리 파라미터다

```
uq_inventory_balance_dim  (법인·사업부·공장·창고·위치·품목·COALESCE(lot)·품질상태·재고상태·소유·COALESCE(소유처))
```

**`groupBy` 로 묶는 축을 고른다**(`W-01-07` §5-1의 보기 3종 = 품목별·LOT별·위치별).

⚠ **L-7 — 묶으면 안 되는 축이 있다.** **소유(`ownership_type_code`)가 다르면 합치지 않는다** — 자사 재고와 고객 지급품을 더하면 오독이다. **`groupBy` 가 무엇이든 소유는 항상 행을 나눈다.**

⚠ **`available_qty` 는 `GENERATED STORED`** 다. 응답에 담되 **화면도 서버도 다시 계산하지 않는다**(L-2).

---

## 5. 오프라인 큐를 계약이 어떻게 담나 *(1단계 확인 — 닫음)*

모바일 10장이 §C 12조항에 걸린다. **세 가지를 계약에 명시한다.**

```http
POST /logistics/putaway-tasks/{id}:complete
Idempotency-Key: <UUID>            ← 필수 (오프라인 대상 오퍼레이션)
                                      ⚠ If-Match 는 붙이지 않는다 (C-9)

{ "businessDate": "2026-08-06", ... }   ← 본문 필드 (C-8 — 클라이언트가 정한다)
```

| 항목 | 계약 표현 | 근거 |
| --- | --- | --- |
| **멱등키** | `Idempotency-Key` **헤더 필수** · 재전송은 **200/209** | C-1 · 설계검토 §3.5 |
| **`business_date`** | **본문 필드** — 서버가 수신 시각으로 채우지 않는다 | **C-8** — `UNIQUE(key, business_date)` 라 날짜가 키의 일부다 |
| **`If-Match`** | 오프라인 대상 오퍼레이션에서 **optional** — 없으면 낙관적 잠금 검사를 건너뛴다 | **C-9** — 큐는 토큰을 싣지 않는다 |

⚠ **`If-Match` 를 optional 로 두는 것은 오프라인 대상에만 적용한다.** 관리웹 전용 오퍼레이션(`W-01-12` 조정 등)은 **required 를 유지**한다. 계약에 그 구분을 적고, 어느 오퍼레이션이 오프라인 대상인지는 **C-5(오프라인 허용은 화면 속성)**를 따른다.

⚠ **발생 시각은 단말 시계다**(C-1 규칙 3) — `occurredAt` 을 본문에 받고 서버 수신 시각(`recordedAt`)과 분리한다. ⬜ **시계 오차 보정은 미결**(C-12).

---

## 6. 이 단계에서 닫은 것과 남은 것

| 1단계 확인 | 상태 |
| --- | --- |
| `putaway_rule` 계약 위치 | ✅ **경로 `/logistics/putaway-rules` · 파일 `mdm-기준정보.json`** — 파일과 네임스페이스는 다른 축이다(§1) |
| 횡단 3종 순서 | ✅ **01 뒤**(`01-리소스도출.md` §1-2) |
| `goods_issue` 유형 분기 | ✅ **`issue_type_code` 실재 — 경로를 나누지 않는다**(§2-3) |
| 상태 전이 동사 | ✅ **넷으로 통일 + 문서 고유 동사**(§2-2) |
| `stock_transfer` 2단계 | ✅ **한 문서 + 두 전이** — `shipped_at`·`received_at` 실측(§2-4) |
| 오프라인 큐 표현 | ✅ **3항목 명시**(§5) |

**남은 것 — 3단계(OpenAPI 작성)에서 정한다.**

| # | 항목 |
| :-: | --- |
| 1 | **문서별 `status_code` 값** — 전부 미확정(맨 `code_t`). `enum` 을 못박지 않고 `x-internal-note` 로 남긴다(G-2) |
| 2 | **`:cancel` 허용 상태 범위** — 문서마다 다르다. 화면 §5·§6에서 도출 |
| 3 | **라인 치환의 단위** — 헤더 전체인지 라인만인지. `A-5`(순서 컬럼 유일 제약) 여부로 갈린다 |

## 변경 이력

| 버전 | 날짜 | 변경 요지 |
| --- | --- | --- |
| v0.1 | 2026-08-06 | 초안 — 실행 2단계. 신설 패턴 **라·마·바**의 URL·동작을 정했다. ⭐ **상태 전이 동사를 넷으로 통일**(`:confirm`·`:post`·`:cancel`·`:request-approval`) — 업무 용어가 아니라 **전이의 성격**으로 짓고, **화면이 두 버튼이면 두 오퍼레이션**이라는 도출 규칙을 함께 못박았다. **`:confirm`↔`:post` 분리**는 「확정했는데 전기 실패」를 표현하기 위함(B-8). **마. 원장 형은 복합 키를 URL에 그대로**(`/{businessDate}/{id}`) — `id` 만으로는 전 파티션 스캔이다. **바. 파생 잔액은 11축이 곧 쿼리**이고 **소유는 `groupBy` 와 무관하게 항상 행을 나눈다**(L-7). **오프라인 큐 3항목**을 계약 표현으로 확정 — 멱등키 헤더 · `business_date` 본문 · **`If-Match` optional(오프라인 대상만)**. 1단계 확인 **6건 전건 종결**(실측 2건이 답을 줬다 — `issue_type_code` · `shipped_at`/`received_at`). 3단계로 넘길 미결 3건. |

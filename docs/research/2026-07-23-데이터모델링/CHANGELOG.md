# 변경 이력

# v3 — ERPNext 벤치마킹 반영

기준: ERPNext(frappe/erpnext) `manufacturing`·`stock`·`subcontracting` 모듈 doctype 스키마와
v2 설계를 대조 검토한 뒤, 사용자가 선택한 7개 항목을 반영했다. v2 원본은 `v2/`에 유지.

- 물리 SQL: PostgreSQL 16에서 전체 DDL 실행 검증 (에러 0), 시드 14+4건 적재 확인,
  `uq_bom_default` 부분 유니크 동작 확인
- 테이블 수: 126 → **127** (신규 1: `putaway_rule`)

| # | 항목 | ERPNext 근거 | 변경 |
|---|---|---|---|
| E-1 | 적치 규칙 마스터 | `putaway_rule.item_code/warehouse/capacity/priority`, `stock_entry_detail.putaway_rule` | 신규 `logistics.putaway_rule`(품목×창고×위치, 수용량·우선순위, 부분 유니크) + `putaway_task.applied_putaway_rule_id` 역참조 |
| E-2 | 반제품 계획 계층 연결 | `production_plan_sub_assembly_item.bom_level/type_of_manufacturing` | `production_order.parent_production_order_id`(자기참조, self CHECK) + `bom_level` |
| E-3 | 작업지시 기본 로케이션 | `work_order.wip_warehouse/fg_warehouse/scrap_warehouse` | `work_order.default_wip_location_id / default_fg_location_id / default_scrap_location_id` (nullable — 기본값 제시·오입고 검증용) |
| E-4 | 운영정책 코드 시드 | `manufacturing_settings` 20개 설정 항목 | `OPERATION_POLICY` 코드그룹 + 14개 정책코드 시드 (ERPNext 대응 10 + 자체 요구 4). v2 "후속 결정" 항목 해소 |
| E-5 | 원장 잔액 스냅샷 | `stock_ledger_entry.qty_after_transaction` | `inventory_transaction_line.from_qty_after_transaction / to_qty_after_transaction` — posting 함수가 잔액 갱신과 동시에 기록, 시점 조회(FR-LT-059) O(1)화 |
| E-6 | 기본 BOM 지정 | `bom.is_default` | `bom.is_default` + 품목당 1개 부분 유니크(`uq_bom_default`) |
| E-7 | IN_TRANSIT 재고상태 | `stock_entry.add_to_transit` | `INVENTORY_STATUS` 코드그룹 시드(AVAILABLE/IN_TRANSIT/ON_HOLD/BLOCKED) — 창고 간 이동 shipped~received 구간 표현, 구조 변경 없음 |

**검토 후 채택하지 않은 항목** (검토 보고서 참조, 필요 시 후속 반영):
BOM 복수 산출물(Co/By-Product·Scrap), 외주 사급자재 자재별 추적, 설비 비가동(downtime_entry),
판정식(acceptance_formula)·확인자(confirmed_by), 준비시간·표준 배치수량, 설비 동시 캐파,
LOT 단위 음수재고 예외, 반품 문서 레벨 역참조.

**ERPNext 대비 v2/v3 구조 유지 결정** (변경 불필요로 확인):
불변 원장+역트랜잭션(vs is_cancelled 플래그), 행 단위 검사 측정(vs reading_1..10 슬롯),
lot_relation 계보(vs parent_batch 포인터), 다차원 inventory_balance(vs Bin), 버전+유효기간 체계,
material_substitution_rule, work_session_worker, routing_operation_dependency.
원가·평가는 ERP 소관으로 명시(3-3).

---

# v2 변경 이력 — DB 설계 검토 반영

기준: 요구사항 문서(1-1 ~ 2-7) 대비 설계 문서(3-1/3-2/3-3, 물리 SQL) 검토 결과를
**위험도 높은 순서**로 반영했다. 원본은 `base-docs/`에 유지하고 본 디렉터리는 사본이다.

- 물리 SQL: PostgreSQL 16 컨테이너에서 전체 DDL 실행 검증 완료 (에러 0)
- 신규 무결성 트리거 7종 스모크 테스트 통과 (음수재고 차단/허용, LOT 순환, 원장 불변, header 상태 전이, 분할 합계, 마감 차단)
- 테이블 수: 101 → **126** (신규 25)

---

## 🔴 높음

### H-1. 사용자·부서·권한 기준정보 전면 부재
근거: 1-2 사용자·권한 관리(필수 공통), 2-7 NFR-IM-010/011, 3-1 §5.10, 1-3 SCN-20/31

- 신규: `mdm.department`, `app.app_user`, `app.role`, `app.role_permission`, `app.user_role`, `app.user_data_scope`(사업부·공장 접근범위, RLS 연동)
- `mdm.worker`에 `department_id`, `app_user_id`(작업자↔입력자 구분) 추가
- FK 성립: `approval_request.requested_by`, `approval_step.approver_id`, `disposition_decision.decided_by`, `exception_case.assigned_user_id/assigned_department_id`, `nonconformance.responsible_department_id`, `attachment.uploaded_by`, `material_issue_request.requested_by`, `production_plan.confirmed_by`, `work_session_event.performed_by`, `inbound_receipt.received_by`, `shopfloor_receipt.received_by`, `inventory_count_line.counted_by`
- 의도적 제외(문서화): 전 테이블 `created_by/updated_by`(대량 적재 성능), `audit_event.performed_by`(파티션·적재량) — 앱 계층 검증

### H-2. 음수재고 정책과 도메인 제약의 모순
근거: 2-2 FR-MI-025, 2-7 NFR-IM-016 vs `qty_t CHECK(>=0)`

- 신규 도메인 `app.signed_qty_t`(부호 허용) → `inventory_balance.on_hand_qty`에 적용
- 하드 CHECK(`ck_inventory_balance_components`) 제거 → 트리거 `inventory.check_balance_qty()`로 대체:
  음수는 `item.negative_stock_allowed = true`일 때만 허용, 음수 상태에서 예약·피킹·차단 수량 금지,
  양수 상태에서는 기존 성분 검증 유지

### H-3. 특채(concession) 물리 모델 미반영
근거: 논리 §16.12, 2-4 FR-QM-024/033, BR-QM-007, 2-5 FR-LT-034, 1-3 SCN-21

- 신규: `quality.concession` — 사용범위 통제 데이터 포함(허용 작업지시·공정·고객, 유효기간,
  `approved_qty`/`consumed_qty` 상한 CHECK), 승인 필수(`approval_request_id NOT NULL`)

### H-4. 생산라인·작업구역 기준정보 부재 (+논리 §9.2 `planned_line_id` 탈락)
근거: 2-1 FR-WO-006/013/018/034, 2-3 FR-PR-043, 1-3 SCN-02, 1-1 §1

- 신규: `mdm.production_line`(자기참조로 라인→작업구역 계층, `line_type_code`)
- `production_plan.planned_line_id` 복원, `work_order.production_line_id`, `equipment.production_line_id` 추가

### H-5. 작업지시 분할·재작업 계보 부재
근거: 2-1 FR-WO-013/032/039, BR-WO-005, 2-3 FR-PR-035, 1-3 SCN-13

- `work_order`에 `parent_work_order_id`(분할 원본), `rework_source_work_order_id`,
  `rework_source_lot_id`, `rework_source_nonconformance_id` 추가 (+자기참조·유형 CHECK)
- 트리거 `production.check_work_order_split()`: 분할 자식 지시수량 합 ≤ 원본 지시수량
  (미작업 잔여수량 기준 정밀 검증은 앱 계층 책임으로 주석 명시)

### H-6. 적치(putaway) 지시 구조 부재
근거: 2-7 FR-IM-019~023(P0), FR-IM-089, 상태흐름 "적치대기"

- 신규: `logistics.putaway_task` — 입고 Line 근거, 권장/실제 로케이션, 우선순위, 담당자,
  분산적치(다행), 재고 트랜잭션 연결, 미적치 조회용 부분 인덱스

---

## 🟡 중간

| # | 항목 | 변경 |
|---|---|---|
| M-1 | 정정·취소 원본 연결 (2-3 FR-PR-033/034/045, 2-2 FR-MI-034) | `production_result.corrects_production_result_id`, `material_consumption.corrects_consumption_id` 자기참조 FK |
| M-2 | 원장 취소 FK 불성립 (3-3 DB-C20) | `inventory_transaction.reversal_of_business_date` 추가 → 복합 self FK 성립 + 쌍 CHECK |
| M-3 | 라벨·성적서·증빙 발행이력 (2-5 FR-LT-038/039/051/072, 2-4 FR-QM-039, 2-7 FR-IM-084) | 신규 `app.document_issue_log` — 유형·대상·회차·재발행사유·단말기·프린터, 재발행 시 사유 필수 CHECK |
| M-4 | 정책 파라미터 저장 구조 (2-1 FR-WO-033, 2-2 FR-MI-019/023, 2-3 NFR-PR-015, 2-5 FR-LT-001) | 신규 `app.operation_policy` — 범위(사업부·공장·품목·공정)별 수치·문자·불리언 값, 기간 관리 |
| M-5 | 채번규칙 (2-5 FR-LT-005, NFR-LT-016) | 신규 `app.numbering_rule` + `app.numbering_counter` |
| M-6 | 승인경로 설정 (2-6 CR-FR-004) | 신규 `app.approval_route` + `app.approval_route_step`(USER/ROLE/DEPARTMENT 단일 지정 CHECK) |
| M-7 | 검사장비 교정 (2-6 §7.1 P1) | `equipment`에 교정 3컬럼 + 신규 `quality.equipment_calibration` 이력 |
| M-8 | 검사자·작업자 자격 (2-4 FR-QM-014, 2-1 FR-WO-009/022) | 신규 `mdm.worker_qualification`(유형·공정·유효기간) |
| M-9 | 검사계획 파라미터 (2-4 FR-QM-001/005/015/016/017) | `inspection_plan`: routing·승인자, `inspection_plan_version`: AQL·Ac/Re·주기값, `inspection_item_spec`: 측정횟수·검사방법·지정장비 |
| M-10 | 검사실적 멱등키·단말기 (2-4 NFR-QM-002/006) | `inspection_result`에 `idempotency_key UK`, `terminal_id` — 타 원장과 패턴 통일 |
| M-11 | 불량 원인·귀책 (2-6 §7.3, 2-4 FR-QM-026/047) | 신규 `quality.cause_code` + `defect_record`에 추정/확정 원인, 귀책구분·귀책부서, 작업자, 불량설명 |
| M-12 | 부적합 최소 조치사항 (2-6 §7.4) | `nonconformance`에 조치내용·담당자·기한·완료일 4컬럼 |
| M-13 | 선별 실행 결과 (2-4 FR-QM-032) | 신규 `quality.sorting_result` — 수량 분해·기준·결과 LOT 연결 |
| M-14 | `lot.parent_lot_id` 이중 계보 (2-5 FR-LT-053) | "표시용 비정규화, 원천은 lot_relation" 주석 명시(유지 결정) |
| M-15 | 3-3 약속 무결성 트리거 미구현 (DB-C17~C19, TRG-05/06) | 순환 방지, 배분합계 2종(deferred), 원장 불변(header 상태만 허용/line 금지), 마감지시 수정 차단 — 전부 실 DDL로 구현·테스트 |
| M-16 | 사업부 간 품목 매핑 (1-3 SCN-28, 3-3 APP-15) | 신규 `mdm.item_bu_item_map` |
| M-17 | 입하예정(ASN) (2-7 FR-IM-001/009) | 신규 `logistics.asn` + `asn_line`, `inbound_receipt_line.asn_line_id` |
| M-18 | LOT 보류·영향범위 스냅샷 (3-1 §13.5/13.6) | 신규 `trace.lot_hold`(부분수량·해제이력), `trace.impact_analysis`(분석 시점·조건·결과 보존) |
| M-19 | 외주 수량 정산 (1-3 SCN-29, 2-5 FR-LT-062) | 신규 `logistics.subcontract_reconciliation` — 합격·불량·폐기·분실·조정·잔량 분해와 정산확정 |
| M-20 | 반품 속성 (2-7 FR-IM-067/068) | `goods_issue.reason_code/replacement_expected`, `goods_receipt.reason_code`, `goods_receipt_line.original_shipment_lot_allocation_id`(원 출하 LOT) |
| M-21 | `remarks` 공통컬럼 탈락 (논리 §2.2) + 사유 컬럼 (2-2 FR-MI-016, 2-3 FR-PR-029, 2-1 FR-WO-032) | 주요 문서·원장 테이블에 `remarks` 복원, `late_entry_reason_code`(투입·실적), `completion_variance_reason_code`(지시), `change_reason_code`(Running Change) |
| M-22 | Running Change (2-2 FR-MI-021/041) | `material_consumption.replaced_consumption_id` + 사유 코드 |
| M-23 | 실제 사용 공정 구분 (2-2 FR-MI-003) | `bom_component.actual_use_process_id`, `material_consumption.actual_use_process_id` |
| M-24 | 지시 생성시점 공정설정 스냅샷 (2-1 FR-WO-005) | `work_order.operation_settings_snapshot jsonb` |

## 🟢 낮음

- `material_consumption.entered_qty/entered_uom_id` — 입력단위 동시 저장 (2-2 FR-MI-010, 쌍 CHECK)
- `production_result.terminal_id` — 투입과 대칭 (2-3 FR-PR-004/042)
- `routing_operation.standard_yield_rate` — 공정 수율 (2-1 FR-WO-012)
- `terminal_process`에 `can_start_work/can_complete_work/can_cancel_input/can_return_material` (2-1 FR-WO-024 등)
- `work_order.responsible_worker_id` — 책임 작업자 (2-1 FR-WO-014/016)
- `shipment`에 `driver_name/seal_no/transport_document_no/loading_worker_id` (2-7 FR-IM-063, 1-3 SCN-30)
- `inbound_receipt`에 `dock_location_id`(입하장), `exception_type_code/exception_reason/approval_request_id`(P/O 없는 예외입하, SCN-20/FR-IM-007)
- `inbound_receipt_line`에 `package_count`, `supplier_lot_missing/substitute_lot_reason_code` (FR-IM-002/008)
- `shipment_request_line.shipping_inspection_required` (FR-IM-057)
- `inspection_result.reinspection_reason_code` (FR-QM-030), `inspection_request.coverage_from_at/to_at` (2-6 §7.5)
- `item.storage_condition_code/opened_shelf_life_hours`, `location.storage_condition_code` (SCN-22/25)
- 중복 방지 UK 신설: `uq_lot_relation`(이벤트 기준), `uq_shipment_lot_allocation`

## ⚪ 과함 정리

- `routing_operation_dependency.required_completion_rate` **삭제** — 문서의 부분 진행 통제는 전부 수량 기준(2-1 FR-WO-019/20), 근거 없는 선행 구현
- `serial_number`/`serial_component_relation` **유지** — 요구 근거 미확인이나 `item.serial_control_type_code` 체계와 정합, 범위 확인 필요 항목으로 기록

## 명시적 범위 이연 (누락 아님을 기록)

- 대규모 리콜 사건관리(회수수량·고객통지): 2-6 §11 **P2** — `trace.impact_analysis`가 분석 스냅샷까지만 커버
- 설비 가동/비가동 이력(OEE): 1-2가 차기 확장으로 분류 — 작업 세션 기반 중지는 `work_session_event`로 커버
- 도크 스케줄·팔레트 개체 추적·3PL API: 2-7 §9 P2

## 미해결(후속 결정 필요)

- LOT 관계유형 코드 시드: 2-5 FR-LT-053의 12유형 vs 논리 §17.2의 7유형 — 시드 데이터 작성 시 12유형 기준으로 통일할 것
- 사이클타임 단위: 물리 모델은 초 단위 고정(`standard_cycle_time_sec`) 유지 — 논리 문서 표기를 물리에 맞춰 수정

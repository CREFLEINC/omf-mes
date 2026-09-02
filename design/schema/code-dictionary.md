# 코드 사전 (2026-09-02)

> ⭐ **1차 완성 — 103키 / 257자리.** 공유계약 `G-32` 등록부 **62그룹 전부**와 계약이
> `enum` 으로 닫은 **41종**을 담는다. `check-code-dictionary.py` 가 ⓪ 규칙으로 «막는다» —
> 등록부에 이름이 오르면 여기에도 행이 있어야 한다.
>
> ⛔ **값을 지어내지 않았다.** 원천은 넷이고 행마다 「근거」 칸에 어디서 왔는지 적었다 —
> ① 계약 `description` 산문 ② `omf-mes#198` 시드(`design/raw/…/공통코드값목록-제안안`)
> ③ 공유계약 `G-32` 등록부 표 ④ 못 찾으면 **⬜ 로 세어서 남겼다**.
>
> ⭐ **드러난 것 — 「안 정한 값」은 3개뿐이었다.** 등록부 62그룹 중 45그룹의 값이
> **이미 저장소 어딘가에 적혀 있었다.** 미결의 대부분은 결정 부재가 아니라 **기록 분산**이다.
> 옛 서술: ~~시험판이다 · 653개 중 41개만 담았다~~ (2026-09-02 1~3단계로 해소)

## 왜 만드나

한 코드 값이 저장소 **100곳 안팎**에 흩어져 있다(실측 — `documentTypeCode` 114곳 ·
`reasonCode` 442곳). 그런데 수보다 나쁜 것이 셋이다.

| # | 무엇 | 실측 |
| :-: | --- | --- |
| ① | **같은 값이 세 이름으로 불린다** | 계약 `documentTypeCode` · 모델 `document_type_code` · 그룹 `DOCUMENT_TYPE`. grep 이 좁아 규모부터 틀린다(`#145` 가 「5곳」→「39파일 43줄」로 정정한 자리) |
| ② | **판단은 산문에 적히고 산문은 아무도 안 본다** | 계약 2벌에서 문서 유형이 나타나는 모양 — 산문 5 > `enum` 2 |
| ③ | **소유 판정이 그 «안 보는» 자리에 있다** | `A-16`(누가 정하나)이 공유계약 조항 «본문»이라, 기준이 바뀌어도 계약 산문 320곳은 안 따라간다 |

⭐ **키가 ①을, 소유 열이 ③을 고친다.** ②는 절반만 고친다 — 코드 값이 아닌 판단
(「이 화면은 8유형을 덮는다」)은 사전 밖이다.

## 이미 있는 절반 — `G-32` 등록부

⛔ **새로 만드는 것이 아니다.** 공유계약 `G-32` 에 **62그룹**이 등록돼 있고
`check-code-group-pointer.py` 가 게이트로 본다. ✅ **구멍 셋은 2026-09-02 에 전부 닫혔다.**

| # | 구멍 |
| :-: | --- |
| ① | ~~사전이 이미 «둘»이고 손으로 맞춘다~~ ✅ **해소** — 실은 **셋**이었다(조항 산문 52 · 계수 괄호 고유 4 · 검사기 상수 56). 조항 안에 「기계가 읽는 표」를 세우고 검사기가 그 표를 읽게 했다 — **사본이 없다**(`#390`) |
| ② | ~~세 갈래 중 «하나»만 담는다~~ ✅ **해소** — 계약이 `enum` 으로 닫은 **41종 78자리**를 전수로 훑어 담았다. 그 과정에서 **같은 프로퍼티 이름인데 값집합이 갈린 자리 4쌍**이 드러나 키를 갈랐다(`dispositionTypeCode` ×2 · `transitionCode` ×2) |
| ③ | ~~키가 없다~~ ✅ **해소** — `CD-` 접두 키 **103개**. 그룹 이름과 키가 분리돼 「같은 그룹을 여러 키가 쓰는가」·「같은 이름이 다른 값집합인가」를 기계가 판정한다 |

## 키 규약

```
CD-<계열>-<축>
```

- ⛔ **키는 절대 중복하지 않는다.** 값(코드 이름)은 중복해도 된다
- **접두어 `CD-`** — 이 저장소에 이미 도는 여섯과 겹치지 않는다:
  공유계약 조항 `A-16`~`L-11`(A~L 이 다 찼다) · `DR-004` · `E-9` · `REQ-PR-0021`/`FR-IM-076` ·
  화면 `W-01-13`/`P-02-05` · 이슈 `#145`
- ⭐ **한 글자를 못 쓴다** — 그리고 접두어 없이 번호만 쓴 것이 실제로 사고를 냈다
  (`E-9` 가 조항·회신·예외 셋을 가리켰고 `#24` 가 이슈와 QA 둘을 가리켰다 — `#375`)

## 소유 — `A-16` 판정 결과

| 값 | 뜻 | 계약에서 | `W-06-06` 에서 |
| --- | --- | --- | --- |
| `enum` | **설계가 정한다** | 계약이 값 목록을 갖는다. ⛔ 등록부에 안 올린다 | — |
| `registry` | **고객이 운영 중에 정한다**(`G-31` 마스터안전형) | `codeGroupCode=` 포인터만. 등록부(`G-32`)에 오른다 | ✅ 편집 가능 |
| **`registry-system`** | **설계가 정한 값을 마스터에 «싣는다»** | 포인터 + 등록부. ⭐ `enum` 이 아닌 이유는 **표시명**이다 | ⛔ **편집 잠금** |
| `derived` | **서버가 파생한다** | 화면이 안 보낸다 | — |

### ⭐ `registry-system` 은 왜 필요한가 — 2026-09-02 신설

`enum` 과 `registry` 둘로는 **상태값을 담을 자리가 없다.**

| 물음 | `enum` | `registry` |
| --- | :-: | :-: |
| 값을 우리가 정하나 | ✅ | ⛔ |
| 표시명(한국어·베트남어)이 함께 오나 | ⛔ **화면이 갖는다** | ✅ |

이 시스템은 **2개국어**다. 상태값을 `enum` 으로 박으면 「접수」를 베트남어로 뭐라 쓸지
**프론트가 하드코딩**한다. 그래서 `INSPECTION_REQUEST_STATUS` 는 **확정 5값인데도 포인터**로
두었다(`omf-mes#170`) — 값은 우리가 정하고 표시명은 마스터에서 받는다.

⛔ **그런데 그러면 고객이 `W-06-06` 에서 그 값을 지울 수 있다.** `G-32` 가 경고한 자리이고
(「고객이 정할 마스터에 **동작이 걸리는 값**이 섞이지 않게 한다」) `W-06-06` **미결 9** 가
「**셋째 축이 필요하다**」로 열어 둔 자리다.

⚠ **지금 그 표시는 실효가 없다.** 선례 `WORK_SESSION_EVENT_TYPE` 의 「⛔ 시스템 소유」는
**등록부 산문의 괄호 하나**뿐이고 읽는 기계가 없다 — 검사기 `REGISTRY` 에는 이름만 있고,
`W-06-06` 화면도 축이 둘뿐이다. **이 열이 그 첫 「기계가 읽는 근거」다.**

⛔ **서버가 내려줄 플래그가 아직 없다** — 코드그룹 마스터에 「시스템 소유」 칸이 필요하다.
`A-11` v4.6 대로 **기다리지 않고 작업 통지**로 냈다 — **`omf-mes#386`**.

---

## 사전 — **103키 / 257자리**

| 소유 | 키 |
| --- | :-: |
| `enum` — 계약이 닫았다 | **41** |
| `registry` — 고객이 늘린다 | **40** |
| `registry-system` — ⛔ 고객 편집 불가 | **22** |

⬜ **값을 못 찾은 것은 3키뿐이다** — `CD-APP-USER-STATUS`(뜻은 확정, 코드 문자열이 없다) ·
`CD-GOODS-RECEIPT-REASON`·`CD-JUDGMENT-TYPE`(고객이 운영 중에 설정하는 마스터라 **없는 것이 정상**).

⛔ **열이 일곱이다 — 「키·값」 둘로는 서지 않는다.** 테스트베드가 그것을 실물로 증명했다
(§ 아래 「형식이 두 번 틀렸다」).

| 열 | 무엇 | 중복 |
| --- | --- | :-: |
| **키** | 이 코드를 가리키는 유일한 이름 | ⛔ **절대 불가** |
| **값** | ⭐ **언제나 «실제 코드 문자열»**이다 — 그룹 이름이 아니다 | ✅ 가능 |
| **그룹** | `codeGroupCode` — 서버 마스터에서 받을 때 쓰는 이름. `enum` 갈래는 `—` | ✅ |
| **프로퍼티** | 계약이 부르는 이름 | ✅ **`statusCode` 는 97자리에서 중복한다** |
| **소유** | 값을 누가 정하고 어디서 오나 — 아래 표 | |
| **자리** | 계약에서 이 키가 걸리는 자리 수. 검사기가 실물과 대조한다 | |
| **근거** | 어디서 나온 값인가 | |

⭐ **「값이 완전한 목록인가 예시인가」는 «소유» 열이 말한다** — 값 열의 «모양»으로 가르지 않는다.

| 소유 | 값 열의 뜻 |
| --- | --- |
| `enum` | **완전 목록** — 계약이 닫았다. 이 밖의 값은 400 이다 |
| `registry` | **초기 시드** — 고객이 `W-06-06` 에서 늘리거나 바꾼다 |
| `registry-system` | **완전 목록** — 우리가 정했고 마스터에 실린다. 고객은 편집 불가 |
| `derived` | — 화면이 안 보낸다 |

| 키 | 값 | 그룹 | 프로퍼티 | 소유 | 자리 | 근거 |
| --- | --- | --- | --- | :-: | :-: | --- |
| `CD-ACKNOWLEDGE-DECISION` | `APPLY` `PROCEED` | — | `acknowledgeDecisionCode` `decisionCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `ProductionOrder` · `ProductionOrderAcknowledge`(`production-02생산실행`) |
| `CD-ACTION` | `CREATE_HOLD` `RELEASE_HOLD` | — | `actionCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `LotStatusTransition`(`quality-03품질`) |
| `CD-APP-USER-STATUS` | ⬜ **미상** | `APP_USER_STATUS` | `statusCode` | `registry` | 4 | ⬜ **뜻은 확정, 코드 문자열이 없다** — 계약이 「재직·휴직·퇴사 등」으로 «한국어 뜻»만 적었다. `§G` 규약대로 「확정된 뜻을 영문 SNAKE 로 옮긴다」를 적용할 자리이나 그 도출은 아직 안 했다. ⛔ 계정 사용 가부는 이 값이 아니라 `isActive` 가 정한다 |
| `CD-APPROVAL-REQUEST-STATUS` | `PENDING` `APPROVED` `REJECTED` | `APPROVAL_REQUEST_STATUS` | `statusCode` | `registry-system` | 2 | 결재 요청. `W-CO-09` §3 목업 · 사용자 결정 2026-09-02 |
| `CD-APPROVAL-STEP-DECISION` | `APPROVED` `REJECTED` | — | `decisionCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `ApprovalStep`(`app-공통`). ⚠ 「대기」를 값으로 두지 않는다 — 비어 있으면 아직 결재하지 않은 단계다. ⛔ 생산 사전점검의 `CD-DECISION` 과 축이 다르다 |
| `CD-APPROVAL-TARGET-TYPE` | `GOODS_ISSUE` `GOODS_RECEIPT` `INBOUND_LOT` `INBOUND_RECEIPT` `INVENTORY_ADJUSTMENT` `PURCHASE_ORDER` `SHIPMENT` | — | `targetTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `ApprovalTarget`(`app-공통`). ⭐ **2026-09-02 개명** — `CD-TARGET-TYPE` 은 이름에 자리가 없어 «범용»처럼 읽혔는데 실은 결재 전용이다. 같은 축의 형제 넷(첨부·문서발행·보전·감사)이 서면서 접두 규약을 통일했다(사용자 결정 결정 1 「가」) |
| `CD-APPROVAL-TYPE` | `GOODS_ISSUE_DISPOSAL` `INVENTORY_ADJUSTMENT` `PURCHASE_ORDER` `INBOUND_RECEIPT_CANCEL` `GOODS_RECEIPT_CANCEL` `GOODS_ISSUE_CANCEL` `SHIPMENT_CANCEL` `IQC_SKIP` | — | `approvalTypeCode` | `enum` | 5 | 승인 유형 8값. `#336` · 사용자 확정 2026-09-01 |
| `CD-APPROVER-TYPE` | `DEPARTMENT` `ROLE` `USER` | — | `approverTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `ApprovalRouteStep` · `ApprovalRouteStepInput`(`app-공통`) |
| `CD-ATTACHMENT-TARGET-TYPE` | `NOTICE` `WAREHOUSE` | — | `targetTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `Attachment`(`app-공통`). ⭐ **두 화면이 이미 문자열을 스펙에 적어 두고 있었다** — `W-CO-08` §3 창고 도면 · `W-CO-04` §4 공지 첨부 |
| `CD-AUDIT-EVENT-TYPE` | `CREATE` `UPDATE` `DELETE` `GRANT` `REVOKE` ⬜ | `AUDIT_EVENT_TYPE` | `eventTypeCode` | `registry-system` | 2 | 감사 이벤트 유형. ⭐ `GRANT`·`REVOKE` 의 근거는 `W-CO-02` §8-8 — 「누가 언제 권한을 줬나」가 남는 곳이 그동안 하나도 없었다. ⛔ 무엇을 기록할지는 시스템이 정한다 |
| `CD-AUDIT-TARGET-TYPE` | `APP_USER` `ROLE` ⬜ | `AUDIT_TARGET_TYPE` | `targetTypeCode` | `registry-system` | 2 | ⛔ **시스템 소유** — 감사 대상은 우리 표 이름이라 고객이 늘릴 수 없다. ⚠ `enum` 으로 닫지 않는다 — 두 값이 들었다고 목록이 닫힌 것이 아니다(`A-21`). 근거: 사용자 결정 2026-09-01 · `W-CO-02` §8-8 |
| `CD-CALIBRATION-HISTORY-TYPE` | `CALIBRATION` `CHECK` ⬜ | `CALIBRATION_HISTORY_TYPE` | `historyTypeCode` | `registry` | 3 | 계측기 이력 유형. ⭐ **2026-09-02 사용자 결정으로 시스템이 «이름으로 지목하는» 값이 `CALIBRATION` 하나가 됐다** — 사용 가부 판정이 「열린 «수리» 이력」 대신 `blocksUse`+`clearedAt` 를 읽는다(`W-05-11` §5-2). 그래서 「수리」·「폐기」의 문자열을 우리가 정할 필요가 없고, 계약이 원래 적은 「관리자 설정형」이 그제서야 성립한다 |
| `CD-CANCELABLE-DOCUMENT-TYPE` | `INBOUND_RECEIPT` `GOODS_RECEIPT` `GOODS_ISSUE` | — | `documentTypeCode` | `enum` | 1 | 취소할 수 있는 문서. 같은 계약 · 「자리마다 닫는다」 |
| `CD-COMPLETION-JUDGMENT` | `NORMAL` `OVER` `UNDER` | — | `completionJudgmentCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `LotProgress` · `WorkOrderProgress`(`logistics-01자재창고`) |
| `CD-CONTROL-LEVEL` | `BLOCK` `OFF` `WARN` | — | `controlLevelCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `PrecheckDecision` · `PrecheckDecisionCreate`(`production-02생산실행`) |
| `CD-CONTROL-OVERRIDE-REASON` | `EMERGENCY_WORK_ORDER` `OTHER` | `CONTROL_OVERRIDE_REASON` | `reasonCode` | `registry` | 3 | 통제 우회 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-CYCLE-TYPE` | `DAY` `WEEK` `MONTH` `YEAR` | `CYCLE_TYPE` | `pmCycleUnitCode` `calibrationCycleTypeCode` `cycleTypeCode` | `registry-system` | 8 | 기간 단위. ⭐ **반례** — 아래 참조. ⛔ **값을 사전에 적자 결손이 드러났다**(2026-09-02) — `pmCycleUnitCode` 산문이 「일 또는 월」 **2값**으로 낡아 있었다. `#188` 이 4값으로 합쳐 확정했는데 형제 자리만 따라갔다. ⭐ **소유 = `registry-system` 확정**(사용자 결정 2026-09-02) — 공유계약 G-32 등록부 표와 같다 |
| `CD-DAY-TYPE` | `HOLIDAY` `PARTIAL` `WORKING` | — | `dayTypeCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `WorkCalendarDay`(`mdm-기준정보`) |
| `CD-DECISION` | `BLOCKED` `OVERRIDDEN` `PASSED` `WARNED` | — | `decisionCode` | `enum` | 3 | 계약이 `enum` 으로 닫은 값 — `PrecheckDecision` · `PrecheckDecisionCreate`(`production-02생산실행`) |
| `CD-DEFECT-CODE-DISPOSITION-TYPE` | `REWORKABLE` `SCRAP` | — | `dispositionTypeCode` | `enum` | 3 | 계약이 `enum` 으로 닫은 값 — `DefectCode` · `DefectCodeCreate`(`mdm-기준정보`) |
| `CD-DEFECT-RECORD-SOURCE` | `FIELD` `PQC` `OQC` `REPAIR` `CLAIM` | `DEFECT_RECORD_SOURCE` | `sourceCode` | `registry-system` | 3 | CD-DEFECT-RECORD-SOURCE 는 불량 기록 원천 5값. 결정 09 |
| `CD-DELAY-STATUS` | `DELAYED` `ON_TIME` `UNDETERMINABLE` | — | `delayStatusCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `WorkOrderProgress`(`production-02생산실행`) |
| `CD-DIRECTION` | `INBOUND` `OUTBOUND` | — | `directionCode` | `enum` | 6 | 계약이 `enum` 으로 닫은 값 — `IntegrationMessage` · `InterfaceDefinition`(`mdm-기준정보`) |
| `CD-DISPOSITION-DECISION-DISPOSITION-TYPE` | `NORMAL` `REWORK` `SCRAP` | — | `dispositionTypeCode` | `enum` | 3 | 계약이 `enum` 으로 닫은 값 — `DispositionDecision` · `DispositionDecisionCreate`(`quality-03품질`) |
| `CD-DISPOSITION-PROGRESS` | `COMPLETED` `NOT_STARTED` `PARTIAL` | — | `dispositionProgressCode` `followUpStatusCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `DispositionDecision` · `Nonconformance`(`quality-03품질`) |
| `CD-DOCUMENT-ISSUE-TARGET-TYPE` | `GOODS_ISSUE_LINE` `HANDLING_UNIT` `INSPECTION_RESULT` `LOCATION` `LOT` `MOLD` `SERIAL_NUMBER` | — | `targetTypeCode` | `enum` | 4 | 계약이 `enum` 으로 닫은 값 — `DocumentTarget` · `DocumentIssueSummary`(`app-공통`). ⭐ **뜻 일곱은 §3-7 대응표가 이미 못박았고 문자열만 없었다** — 2026-09-02 §G 로 도출. 이 미결이 화면의 유형 선택칸을 비활성으로 묶고 있었다 |
| `CD-DOWNTIME-REASON` | `EQUIPMENT_FAILURE` `MOLD_CHANGE` `MATERIAL_WAIT` `LABOR_WAIT` `PREVENTIVE_MAINTENANCE` `OTHER` | `DOWNTIME_REASON` | `reasonCode`(쿼리) | `registry` | 2 | 설비 비가동 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-EQUIPMENT-BREAKDOWN-STATUS` | `RECEIVED` `HANDLING` `DONE` | `EQUIPMENT_BREAKDOWN_STATUS` | `statusCode` | `registry-system` | 2 | 고장 접수. **값이 계약 산문에 이미 있었다**(2026-09-02 꺼냄) · `W-05-04` |
| `CD-EQUIPMENT-INSPECTION-JUDGMENT-METHOD` | `VISUAL` `MEASUREMENT` | `EQUIPMENT_INSPECTION_JUDGMENT_METHOD` | `judgmentMethodCode` | `registry-system` | 4 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-EQUIPMENT-INSPECTION-TYPE` | `DAILY` `MONTHLY` `MAINTENANCE` | `EQUIPMENT_INSPECTION_TYPE` | `inspectionTypeCode` | `registry` | 8 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-EQUIPMENT-STATUS` | `IN_SERVICE` `DISPOSED` | `EQUIPMENT_STATUS` | `statusCode` | `registry-system` | 4 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-EQUIPMENT-TYPE` | `INJECTION_MOLDING` `PRESS` `WATER_HEATER` | `EQUIPMENT_TYPE` | `equipmentTypeCode` | `registry` | 4 | 설비 계열. `#186` · 통지 `client#415` |
| `CD-EVENT-TYPE` | `HELD` `RELEASED` | — | `eventTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `LotHoldEvent`(`quality-03품질`) |
| `CD-EXTERNAL-SYSTEM` | `EQUIPMENT_STANDARD_IF` `TRACKING_SYSTEM` `UNIERP` | — | `externalSystemCode` | `enum` | 7 | 계약이 `enum` 으로 닫은 값 — `InterfaceDefinition` · `InterfaceDefinitionCreate`(`mdm-기준정보`) |
| `CD-FIFO-POLICY` | `FIFO` `FEFO` | `FIFO_POLICY` | `fifoPolicyCode` | `registry-system` | 2 | CD-FIFO-POLICY 는 품목별 선입선출 정책. QA #28 |
| `CD-FROM-INVENTORY-STATUS` | `AVAILABLE` `BLOCKED` `IN_TRANSIT` `ON_HOLD` | — | `fromInventoryStatusCode` `inventoryStatusCode` `toInventoryStatusCode` | `enum` | 6 | 계약이 `enum` 으로 닫은 값 — `GoodsReceiptLine` · `GoodsReceiptLineCreate`(`logistics-01자재창고`) |
| `CD-GOODS-ISSUE-DESTINATION-TYPE` | `LOCATION` `PARTNER` `DISPOSAL_SITE` | — | `destinationTypeCode` | `enum` | 2 | 출고 도착지. ⚠ 계약 `enum` 에 `null` 이 함께 있다(nullable). `#337` |
| `CD-GOODS-ISSUE-REASON` | `IQC_FAIL` `OVER_RECEIPT` `DEFECT_AFTER_RECEIPT` `WRONG_SHIPMENT` `OTHER` | `GOODS_ISSUE_REASON` | `reasonCode` | `registry` | 3 | 출고 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-GOODS-ISSUE-SOURCE-DOCUMENT-TYPE` | `DISPOSITION_DECISION` `GOODS_RECEIPT` `PICKING_ORDER` | — | `sourceDocumentTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `GoodsIssue` · `GoodsIssueCreate`(`logistics-01자재창고`). ⭐ **2026-09-02 개명** — 출고 전용인데 이름에 자리가 없어 «범용»처럼 읽혔다(사용자 결정 결정 1 「가」) |
| `CD-GOODS-RECEIPT-DISPOSITION` | `IQC_PASSED` `SAMPLING_NOT_REQUIRED` `URGENT_IQC_WAIVED` | — | `receiptDispositionCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `/trace/lots`(`logistics-01자재창고`). ⭐ 값 집합은 `W-01-10` §3·§5-1·§5-5 가 이미 확정했고 문자열만 없었다 |
| `CD-GOODS-RECEIPT-REASON` | ⬜ **미상** | `GOODS_RECEIPT_REASON` | `reasonCode` | `registry` | 2 | ⭐ **값이 없는 것이 정상이다** — 고객이 운영 중에 설정하는 마스터다(`G-31` · 2026-08-31 사용자 확정). 계약이 「확정을 기다리지 않는다 · 목록은 실행 시점에 마스터에서 온다」로 못박았다. 초기 시드를 우리가 줄지는 별건 |
| `CD-GOODS-RECEIPT-SOURCE-DOCUMENT-TYPE` | `INBOUND_RECEIPT` `SHIPMENT` `PRODUCTION_RESULT` `SUBCONTRACT_ISSUE` | — | `sourceDocumentTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `GoodsReceipt`·`GoodsReceiptCreate`(`logistics-01자재창고`). 근거 넷: `W-01-13`(입하→입고) · `W-04-06`(반품) · `M-04-04`(생산 실적·외주 회수). ⭐ **비울 수 있다**(2026-08-31 사용자 확정) — `NONE` 을 값으로 두지 않는다 |
| `CD-HANDLING-UNIT-TYPE` | `BOX` `CART` `PALLET` | `HANDLING_UNIT_TYPE` | `handlingUnitTypeCode` | `registry` | 3 | 취급단위 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INBOUND-RECEIPT-EXCEPTION-TYPE` | `CUSTOMER_SUPPLY` `FREE_SAMPLE` `URGENT_RECEIPT` `OVER_DELIVERY` | `INBOUND_RECEIPT_EXCEPTION_TYPE` | `exceptionTypeCode` | `registry` | 3 | 입하 예외 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INBOUND-VARIANCE-REASON` | `DAMAGED` `MISLABELED` `SUPPLIER_MISSHIP` `PACKAGING_DEFECT` `OTHER` | `INBOUND_VARIANCE_REASON` | `reasonCode` | `registry` | 2 | 입하 차이 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INBOUND-VARIANCE-TYPE` | `SHORTAGE` `ITEM_MISMATCH` `UNREGISTERED_ITEM` | `INBOUND_VARIANCE_TYPE` | `varianceTypeCode` | `registry-system` | 2 | 공유계약 `G-32` 등록부 표의 근거 칸에서 옮겼다 |
| `CD-INSPECTION-FREQUENCY` | `WORK_ORDER` `PRODUCTION_LOT` `MATERIAL_LOT` `SHIFT` `TIME_INTERVAL` `QUANTITY_INTERVAL` `EQUIPMENT_MOLD_CHANGE` `USER_REQUEST` | `INSPECTION_FREQUENCY` | `inspectionFrequencyCode` | `registry` | 3 | 검사 주기. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INSPECTION-FREQUENCY-INTERVAL-UOM` | `HOUR` `QUANTITY` | `INSPECTION_FREQUENCY_INTERVAL_UOM` | `frequencyIntervalUomCode` | `registry-system` | 3 | 검사 주기의 «단위». ⭐ SQL 1770 주석이 「주기 파라미터: N시간·N수량」이라 두 축을 적었다. ⛔ 기준단위 마스터(`mdm.uom`)와 다른 축이다 |
| `CD-INSPECTION-ITEM-SPEC-DATA-TYPE` | `NUMERIC` `TEXT` `BOOLEAN` | `INSPECTION_ITEM_SPEC_DATA_TYPE` | `dataTypeCode` | `registry-system` | 2 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-INSPECTION-ITEM-SPEC-METHOD` | `MEASUREMENT` `VISUAL` `FUNCTIONAL` | `INSPECTION_ITEM_SPEC_METHOD` | `inspectionMethodCode` | `registry` | 2 | 검사 항목 판정 방법. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INSPECTION-MEASUREMENT-JUDGMENT` | `ACCEPTED` `REJECTED` | `INSPECTION_MEASUREMENT_JUDGMENT` | `judgmentCode` | `registry-system` | 2 | 검사 **항목** 판정 — 규격에 드는지 아닌지 둘뿐. `#179` · ⭐ 종합과 **값이 겹치는데 그룹이 다르다**. ⭐ **소유 = `registry-system` 확정**(사용자 결정 2026-09-02) — 공유계약 G-32 등록부 표와 같다 |
| `CD-INSPECTION-OVERALL-JUDGMENT` | `ACCEPTED` `REJECTED` `HELD` | `INSPECTION_RESULT_OVERALL_JUDGMENT` | `overallJudgmentCode` | `registry-system` | 7 | 검사 **종합** 판정 — 보류 수량(`held_qty`)이 있다. `#179`. ⭐ **소유 = `registry-system` 확정**(사용자 결정 2026-09-02) — 공유계약 G-32 등록부 표와 같다 |
| `CD-INSPECTION-REQUEST-STATUS` | `REQUESTED` `IN_PROGRESS` `COMPLETED` `SKIPPED` `CANCELLED` | `INSPECTION_REQUEST_STATUS` | `statusCode` | `registry-system` | 2 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-INSPECTION-RESULT-STATUS` | `DRAFT` `CONFIRMED` | `INSPECTION_RESULT_STATUS` | `statusCode` | `registry-system` | 4 | 검사 성적서 상태. ⛔ **계약 7벌에서 «유일한» 한국어 enum**(「작성중」·「확정」)이던 자리를 다른 상태 그룹과 같은 모양으로 맞췄다 · ⛔ **변경 통지 대상** · 사용자 결정 2026-09-02 |
| `CD-INSPECTION-SAMPLING-METHOD` | `FULL_INSPECTION` `SAMPLE_BY_UNIT` `SAMPLE_BY_LOT` | `INSPECTION_SAMPLING_METHOD` | `samplingMethodCode` | `registry` | 3 | 검사 샘플링 방식. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INSTRUMENT-TYPE` | `CALIPER` `MICROMETER` `GAUGE` | `INSTRUMENT_TYPE` | `equipmentTypeCode` | `registry` | 4 | 계측기 계열. **같은 컬럼에 두 계열**(`G-32` · `#219`) · 통지 `client#404` |
| `CD-INTEGRATION-MESSAGE-STATUS` | `PENDING` `PROCESSING` `DONE` `FAILED` | `INTEGRATION_MESSAGE_STATUS` | `statusCode` | `registry-system` | 2 | ERP 연계 메시지. ⭐ 계약이 적어 둔 「최소 구분」 넷을 그대로 확정 · 사용자 결정 2026-09-02 |
| `CD-INTERFACE-TARGET` | `ITEM` `BOM` `ORGANIZATION` `WORKER` `PURCHASE_ORDER` ⬜ | `INTERFACE_TARGET` | `targetCode` | `registry` | 1 | 연계 대상. ⭐ 계약이 «일부러 열어 둔» 자리다 — 그 밖의 값도 받고 막지 않으며 확정 목록 안인지는 `withinConfirmedScope` 가 말한다 |
| `CD-INVENTORY-ADJUSTMENT-REASON` | `COUNT_VARIANCE` `TRANSPORT_DAMAGE` `HOPPER_MEASUREMENT` `SYSTEM_ERROR_CORRECTION` `OTHER` | `INVENTORY_ADJUSTMENT_REASON` | `reasonCode` | `registry` | 3 | 재고조정 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INVENTORY-COUNT-STATUS` | `PLANNED` `IN_PROGRESS` `COMPLETED` | `INVENTORY_COUNT_STATUS` | `statusCode` | `registry-system` | 2 | 재고 실사. ⚠ **전표 상태와 다른 축** — 전기·취소가 없다. `W-01-04` §3 목업 · 사용자 결정 2026-09-02 |
| `CD-INVENTORY-COUNT-TYPE` | `PERIODIC` `ADHOC` `CYCLE` | `INVENTORY_COUNT_TYPE` | `countTypeCode` | `registry` | 3 | 재고실사 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-INVENTORY-RESERVATION-SOURCE-DOCUMENT-TYPE` | `PRODUCTION_ORDER` | — | `sourceDocumentTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `InventoryReservation`(`logistics-01자재창고`). ⭐ `W-02-01` §5-4 가 「P/O 의 자재예약정보가 `production_order` 에 없고 `inventory_reservation` 이 P/O 를 가리킨다」로 세운 축이다(2026-09-02 해소). ⚠ 값이 하나라고 축이 없는 것이 아니다 |
| `CD-INVENTORY-TRANSACTION-SOURCE-DOCUMENT-TYPE` | `GOODS_RECEIPT` `GOODS_ISSUE` `INVENTORY_ADJUSTMENT` `STOCK_TRANSFER` | — | `sourceDocumentTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `InventoryTransaction`(`logistics-01자재창고`). ⭐ 원장 한 줄의 «성격»을 말하는 축이다 — 방향(입고·출고·이동)은 라인의 `from*`/`to*` 가 이미 말한다. ⚠ `STOCK_TRANSFER` 는 추론이라 다른 셋보다 근거가 얕다 |
| `CD-ISSUE-TYPE` | `PRODUCTION` `SUPPLIER_RETURN` `OTHER` `SHIPMENT` | `ISSUE_TYPE` | `issueTypeCode` | `registry` | 3 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-ITEM-TYPE` | `RAW_MATERIAL` `SEMI_FINISHED` `FINISHED` `MERCHANDISE` ⬜ | `ITEM_TYPE` | `itemTypeCode` | `registry` | 2 | 품목 유형. ⭐ 뜻 넷은 2026-08-22 분류표 20 이 「원자재/반제품/제품/상품」으로 이미 적었다 — 문자열만 없었다. ⛔ 예비품을 여기 넣지 않는다(QA #7 「품목 통합 아님」) |
| `CD-JUDGMENT-TYPE` | ⬜ **미상** | `JUDGMENT_TYPE` | ⬜ **프로퍼티가 아니다** — 스키마·경로 설명 | `registry` | 2 | ⭐ **값이 없는 것이 정상이다** — `W-06-04` 판정유형 코드 마스터가 «고객 운영»으로 관리한다. 판정유형마다 물류 통제 속성 6종을 붙이는 구조라 값은 고객이 늘린다. ⚠ **① 계수에 남는 2는 결손이 아니다** — 이 그룹의 포인터는 «프로퍼티»가 아니라 스키마·경로 설명에 있어 검사기가 프로퍼티 축에서 못 센다 |
| `CD-LEVEL` | `EQUIPMENT_GROUP` `PLANT` | — | `levelCode` `targetTypeCode` | `enum` | 4 | 계약이 `enum` 으로 닫은 값 — `WorkCalendarApplication` · `WorkCalendarApplicationUpdate`(`mdm-기준정보`) |
| `CD-LOCATION-TYPE` | `RACK` `FLOOR` `TEMP` `HOPPER` `DEFAULT` ⬜ | `LOCATION_TYPE` | `locationTypeCode` | `registry` | 3 | 위치의 «물리적 형태». ⭐ 축은 하나다 — 계층 깊이는 `managementLevelCode` 가 따로 갖는다(2026-08-22 분류표 37). ⭐ 세 화면이 이미 값을 지목했다 — `M-01-07` §5-3 ①안(`TEMP`) · `M-01-09`(`HOPPER`) · `M-01-04`(흡수용 = `DEFAULT`). ⚠ 그 셋은 화면이 «판정»에 쓴다 |
| `CD-LOGISTICS-DOCUMENT-STATUS` | `REGISTERED` `POSTED` `CANCEL_REQUESTED` `CANCELLED` | `LOGISTICS_DOCUMENT_STATUS` | `statusCode` | `registry-system` | 19 | 물류 전표 9종 공용. ⭐ `W-01-13` §3 목업이 네 값을 이미 그렸다 — 꺼낸 것이지 정한 것이 아니다. 9종은 `CD-LOGISTICS-DOCUMENT-TYPE` 과 같은 집합이다 · 사용자 결정 2026-09-02 |
| `CD-LOGISTICS-DOCUMENT-TYPE` | `PURCHASE_ORDER` `INBOUND_RECEIPT` `GOODS_RECEIPT` `MATERIAL_ISSUE_REQUEST` `PICKING_ORDER` `STOCK_TRANSFER` `SUBCONTRACT_ISSUE` `SUBCONTRACT_RECEIPT` `GOODS_ISSUE` | — | `documentTypeCode` | `enum` | 3 | 물류 문서 종류. `logistics-01자재창고.json` — `#351` · `06942be` |
| `CD-LOT-CREATE-SOURCE-TYPE` | `INBOUND_RECEIPT_LINE` | — | `sourceTypeCode` | `enum` | 1 | ⭐ 쓰는 쪽은 **1값으로 닫혀 있다**(`#354`). 읽는 쪽(`CD-LOT-SOURCE-TYPE`)과 «값집합이 달라» 키를 가른다 — `B-28` |
| `CD-LOT-EXTERNAL-IDENTIFIER-TYPE` | `SUPPLIER_LOT` `ERP_LOT` `CUSTOMER_LOT` `SUBCONTRACTOR_LOT` | `LOT_EXTERNAL_IDENTIFIER_TYPE` | `identifierTypeCode` | `registry` | 2 | LOT 외부식별자 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-LOT-HOLD-REASON` | `INCOMING_INSPECTION_WAIT` `FOREIGN_MATTER_SUSPECTED` `DIMENSION_ABNORMAL` `APPEARANCE_ABNORMAL` `CLAIM_RECALL` `OTHER` | `LOT_HOLD_REASON` | `holdReasonCode` `reasonCode` | `registry` | 6 | LOT 보류 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-LOT-HOLD-RELEASE-REASON` | `RETEST_PASS` `RETEST_FAIL` `INVESTIGATION_CLEARED` `MANAGER_OVERRIDE` | `LOT_HOLD_RELEASE_REASON` | `releaseReasonCode` | `registry` | 4 | 공유계약 `G-32` 등록부 표의 근거 칸에서 옮겼다 |
| `CD-LOT-LIFECYCLE-HISTORY-EVENT-TRANSITION` | `L1` `L2` `L3` | — | `transitionCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `LotLifecycleHistoryEvent`(`logistics-01자재창고`) |
| `CD-LOT-LIFECYCLE-STATUS` | `WAITING` `ACTIVE` `VOIDED` | `LOT_LIFECYCLE_STATUS` | `lifecycleStatusCode` | `registry-system` | 1 | LOT 선발행 슬롯 생명주기 — 품질 판정 축과 다르다 |
| `CD-LOT-SOURCE-TYPE` | `INBOUND_RECEIPT_LINE` `RECYCLE_ENTRY` | `LOT_SOURCE_TYPE` | `sourceTypeCode` | `registry-system` | 1 | CD-LOT-SOURCE-TYPE 는 LOT 발생 원천 |
| `CD-LOT-STATUS` | `NORMAL` `DEFECTIVE` `INSPECTION_PENDING` `SCRAPPED` | `LOT_STATUS` | `fromQualityStatusCode` `lotStatusCode` `qualityStatusCode` `statusCode` `targetLotStatusCode` `toQualityStatusCode` | `registry-system` | 19 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-LOT-STATUS-HISTORY-EVENT-TRANSITION` | `C10` `C14` `C15` `C4` `C5` `C6` `C7` `C8` `C9` | — | `transitionCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `LotStatusHistoryEvent`(`logistics-01자재창고`) |
| `CD-LOT-TYPE` | `MATERIAL` `PRODUCTION` `PRODUCT` | `LOT_TYPE` | `lotTypeCode` | `registry-system` | 8 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-MAINTENANCE-INSPECTION-RESULT` | `PASS` `FAIL` | — | `overallResultCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `/maintenance/inspections`(`equipment-05설비툴`). ⭐ 문자열 근거는 «같은 파일의 일관성» — `Calibration.resultCode` 가 이미 `PASS`·`FAIL` 을 쓴다. 「`OK`」는 저장소 다른 곳에 용례가 없다 |
| `CD-MAINTENANCE-ORDER-ITEM-STATUS` | `PLANNED` `DONE` `NA` | `MAINTENANCE_ORDER_ITEM_STATUS` | `statusCode` | `registry-system` | 1 | 보전 지시 **항목**. ⚠ 지시 전체와 **다른 축**이다 |
| `CD-MAINTENANCE-ORDER-STATUS` | `ISSUED` `DONE` `CANCELLED` | `MAINTENANCE_ORDER_STATUS` | `statusCode` | `registry-system` | 2 | 보전 지시. 같음 · `W-05-05` |
| `CD-MAINTENANCE-TARGET-TYPE` | `EQUIPMENT` `MOLD` | — | `targetTypeCode` | `enum` | 6 | 계약이 `enum` 으로 닫은 값 — `MaintenanceOrder`·`MaintenanceResult`(`equipment-05설비툴`). ⚠ 계측기는 설비의 한 종류라 `EQUIPMENT` 가 덮는다 — `equipmentId` 를 그대로 쓴다 |
| `CD-MAINTENANCE-TYPE` | `CORRECTIVE` `PREVENTIVE` | — | `maintenanceTypeCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `/maintenance/orders`(`equipment-05설비툴`). ⭐ 「예지(`PREDICTIVE`)」를 두지 않는다(사용자 결정 2026-09-02) — 촉발할 트리거가 아직 없다 |
| `CD-MANAGEMENT-LEVEL` | `WAREHOUSE` `ZONE` `RACK` `CELL` | `MANAGEMENT_LEVEL` | `managementLevelCode` | `registry-system` | 3 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-MASTER-VERSION-STATUS` | `DRAFT` `CONFIRMED` `OBSOLETE` | `MASTER_VERSION_STATUS` | `statusCode` | `registry-system` | 3 | 마스터 버전 편집 잠금 — `Routing`·`Bom`·`InspectionPlanVersion` 공용. ⭐ 결정 07 이 Routing 에서 확정한 값을 둘이 준용한다 · 사용자 결정 2026-09-02 |
| `CD-MATERIAL-ISSUE-REQUEST-REASON` | `URGENT_WO_RESPONSE` `SHORTAGE_SUPPLEMENT` `DEFECT_REPLACEMENT` `OTHER` | `MATERIAL_ISSUE_REQUEST_REASON` | `reasonCode` | `registry` | 2 | 공유계약 `G-32` 등록부 표의 근거 칸에서 옮겼다 |
| `CD-MES-CATEGORY` | `NEW` `RECYCLED` | `MES_CATEGORY` | `mesCategoryCode` | `registry-system` | 2 | CD-MES-CATEGORY 는 품목의 신재/재생재 구분. M-01-12 §5-B · DR-006 6-A |
| `CD-NONCONFORMANCE-SEVERITY` | `CRITICAL` `MAJOR` `MINOR` ⬜ | `NONCONFORMANCE_SEVERITY` | `severityCode` | `registry` | 1 | 부적합 심각도. ⭐ 화면 목업이 「심각도 중대」(`W-03-10`)·「심각도 중」(`W-04-07`)을 그려 3단계 축이 이미 서 있었다. ⚠ `#198` 시드 28그룹 목록 «밖»이라 그동안 아무도 세지 않았다 |
| `CD-NONCONFORMANCE-SOURCE` | `PRODUCT` `RETURN` | — | `sourceCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `/quality/nonconformances`(`shipment-04제품출하`). ⭐ 서버가 대상 LOT 의 입고 유형으로 «파생»한다. ⛔ `CD-DEFECT-RECORD-SOURCE` 와 축이 다르다 — 저쪽은 「어디서 발견했나」, 여기는 「어디서 들어온 물건인가」 |
| `CD-NONCONFORMANCE-STATUS` | `NOT_REQUESTED` `PENDING_DECISION` `DECIDED` | `NONCONFORMANCE_STATUS` | `statusCode` | `registry-system` | 2 | 부적합 의뢰·판정 축 |
| `CD-NUMBER-SOURCE` | `MES` `SUPPLIER` | — | `numberSourceCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `LotCreate`(`logistics-01자재창고`) |
| `CD-OUTBOUND-ITEM` | `GOODS_RECEIPT` `PRODUCTION_RESULT` `RETURN` `SHIPMENT_PGI` `STOCK_ADJUSTMENT` | — | `outboundItemCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `OutboundItemSetting` · `OutboundItemSettingInput`(`mdm-기준정보`) |
| `CD-OWNERSHIP-TYPE` | `OWNED` `CUSTOMER_SUPPLIED` `CONSIGNMENT` | `OWNERSHIP_TYPE` | `ownershipTypeCode` | `registry` | 3 | 재고 소유 구분. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-PICKING-ORDER-SOURCE-DOCUMENT-TYPE` | `MATERIAL_ISSUE_REQUEST` `SHIPMENT_REQUEST` | — | `sourceDocumentTypeCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `PickingOrder`(`logistics-01자재창고`). ⭐ 자재 피킹(`M-01-08`)과 제품 피킹(`M-04-01`)이 같은 표를 쓰고 이 값이 둘을 가른다 |
| `CD-PICKING-TYPE` | `MATERIAL` `SHIPMENT` | `PICKING_TYPE` | `pickingTypeCode` | `registry` | 1 | 피킹 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-POLICY` | `FIFO_ENFORCEMENT_LEVEL` `MINOR_STOP_THRESHOLD_MINUTES` `PRECHECK_CONTROL_LEVEL` `SHOT_CONVERSION_ENABLED` `SHOT_CONVERSION_RATIO` | — | `policyCode` | `enum` | 5 | 계약이 `enum` 으로 닫은 값 — `OperationPolicy` · `OperationPolicyCreate`(`app-공통`) |
| `CD-PRINT-DOCUMENT-TYPE` | `MATERIAL_LOT_LABEL` `GOODS_ISSUE_QR` `PRODUCTION_LOT_LABEL` `IDENTIFICATION_TAG` `PACKING_LABEL` `DELIVERY_LABEL` `CERTIFICATE_OF_ANALYSIS` `TOOL_LABEL` `LOCATION_LABEL` | — | `documentTypeCode` `supportedDocumentTypeCodes` | `enum` | 6 | 출력물 종류. `app-공통.json` — `omf-mes#145` · `22c08f5` · 요구서 `app공통출력물` §3-8 |
| `CD-PROCESS-TYPE` | `MACHINING` `ASSEMBLY` `INSPECTION` `PACKAGING` | `PROCESS_TYPE` | `processTypeCode` | `registry` | 1 | 공정 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-PRODUCTION-LINE-TYPE` | `LINE` `WORK_AREA` | — | `lineTypeCode` `groupTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `ProductionLine`·`EquipmentGroup`(`mdm-기준정보`). ⚠ 둘은 «같은 물리 컬럼**(`mdm.production_line.line_type_code`)을 다른 API 이름으로 노출한 것이다 |
| `CD-PRODUCTION-ORDER-STATUS` | `RECEIVED` `UPDATED` `CANCELLED` | `PRODUCTION_ORDER_STATUS` | `statusCode` | `registry-system` | 2 | P/O 상태. ⭐ 「수정됨(UPDATED)」은 사용자가 추가했다 — `W-02-06` 이 P/O 변경 이벤트를 다루는데 그 사실을 담을 값이 없었다 · ERP 매핑 없음(사용자 결정 2026-09-02) |
| `CD-PRODUCTION-PLAN-SPLIT-REASON` | `ENGINEERING_CHANGE` `PART_SHORTAGE` `QUALITY_ISSUE` `SUPPLIER_CHANGE` `OTHER` | `PRODUCTION_PLAN_SPLIT_REASON` | `reasonCode` | `registry` | 1 | 생산계획 분할 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-PRODUCTION-PLAN-STATUS` | `DRAFT` `CONFIRMED` | `PRODUCTION_PLAN_STATUS` | `statusCode` | `registry-system` | 2 | 생산계획 편집 잠금. ⭐ `MASTER_VERSION_STATUS`(작성중·확정·폐기)와 «같은 축»이라 낱말을 맞췄다 — 다만 「폐기」가 이 리소스에 없어 둘이다 |
| `CD-PUTAWAY-TASK-STATUS` | `PENDING` `COMPLETED` `COMPLETED_TEMPORARY` | `PUTAWAY_TASK_STATUS` | `statusCode` | `registry-system` | 2 | 적치 작업. ⭐ **「완료」를 `COMPLETED` 로 정한 근거** — 실측하니 저장소가 도메인으로 갈려 있다: `COMPLETED` 는 실사(01)·작업지시(02)·검사의뢰(03)·처분진행(04) · `DONE` 은 설비 고장(05)·보전지시(05)·보전 항목(05)·연계 메시지. 적치는 물류(01)라 `COMPLETED` 다(사용자 위임 판단 2026-09-02) |
| `CD-PUTAWAY-TASK-TEMPORARY-REASON` | `NO_SPACE` `INSPECTION_HOLD` `LOCATION_UNASSIGNED` `OTHER` | `PUTAWAY_TASK_TEMPORARY_REASON` | `reasonCode` | `registry` | 1 | 임시 위치 적재 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-QUALIFICATION-TYPE` | `PROCESS_OPERATION` `INSPECTOR` `SAFETY` `EQUIPMENT_OPERATION` | `QUALIFICATION_TYPE` | `qualificationTypeCode` | `registry` | 1 | 작업자 자격 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-QUALITY-INSPECTION-TYPE` | `IQC` `PQC` `OQC` | `QUALITY_INSPECTION_TYPE` | `inspectionTypeCode` | `registry-system` | 10 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-QUALITY-ZONE` | ⬜ | `QUALITY_ZONE` | `qualityZoneCode` | `registry` | 3 | 위치의 품질 구역. ⭐ 값을 계약이 닫지 않는다 — 창고 배치·품질관리 절차가 현장마다 다르다. ⛔ LOT 보류(Hold/Release)와의 «관계»가 아직 정의되지 않아(`W-06-07` §8-2) 이 값으로 출고 가부를 판정하지 않는다 — 판정의 정본은 LOT 보류다 |
| `CD-RECEIPT-TYPE` | `MATERIAL` `PRODUCT` `RETURN` `TRANSFER` | `RECEIPT_TYPE` | `receiptTypeCode` | `registry` | 3 | 계약 `description` 산문에 이미 적혀 있던 값을 꺼냈다 |
| `CD-REISSUE-REASON` | `DAMAGED` `LOST` `PRINT_FAILURE` `PACKAGING` `QUANTITY_CHANGE` | `REISSUE_REASON` | `reissueReasonCode` | `registry` | 2 | 출력물 재발행 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-REMAINDER-DISPOSITION` | `CARRY_OVER` `WRITE_OFF` | — | `remainderDispositionCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `WorkOrderClose`(`production-02생산실행`) |
| `CD-REPACK-TYPE` | `MERGE` `RECONFIGURE` `SPLIT` | — | `repackTypeCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `HandlingUnitRepackEvent`(`logistics-01자재창고`) |
| `CD-REPAIR-RESULT` | `FAILED` `SUCCEEDED` | — | `repairResultCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `RepairExecution` · `RepairExecutionReturn`(`production-02생산실행`) |
| `CD-RESERVATION-TYPE` | `MATERIAL` `SHIPMENT` `PRODUCTION` | `RESERVATION_TYPE` | `reservationTypeCode` | `registry` | 1 | 재고예약 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-RESOLVED-FROM-LEVEL` | `EQUIPMENT` `EQUIPMENT_GROUP` `NONE` | — | `resolvedFromLevelCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `EquipmentInspectionItemAssignmentsResponse`(`mdm-기준정보`) |
| `CD-RESOURCE-TYPE` | `EQUIPMENT` `MOLD` `WORKER` | — | `resourceTypeCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `WorkOrderResourcePlan` · `WorkOrderResourcePlanCreate`(`production-02생산실행`) |
| `CD-ROLE` | `RESULT` `SOURCE` | — | `roleCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `HandlingUnitRepackEventLine`(`logistics-01자재창고`) |
| `CD-ROLE-TYPE` | `CUSTOMER` `DISPOSAL` `OTHER` `SUBCONTRACTOR` `SUPPLIER` | — | `roleTypeCode` `roleTypeCodes` | `enum` | 3 | 계약이 `enum` 으로 닫은 값 — `PartnerRole` · `PartnerRolesReplace`(`mdm-기준정보`) |
| `CD-ROUTING-OPERATION-DEPENDENCY-TYPE` | `FINISH_TO_START` `START_TO_START` `FINISH_TO_FINISH` `START_TO_FINISH` | `ROUTING_OPERATION_DEPENDENCY_TYPE` | `dependencyTypeCode` | `registry-system` | 1 | 공정 선후관계. ⭐ 물리 모델이 `DEFAULT 'FINISH_TO_START'` 를 이미 갖고 있다 — 기본값은 확정 |
| `CD-SCOPE` | `BUSINESS_UNIT` `COMPANY` `EQUIPMENT_GROUP` `WORK_ORDER` `WORK_SHIFT` | — | `scopeCode` | `enum` | 3 | 계약이 `enum` 으로 닫은 값 — `Notice` · `NoticeCreate`(`app-공통`) |
| `CD-SHIPMENT-STATUS` | `UNCONFIRMED` `CONFIRMED` `CANCELLED` | `SHIPMENT_STATUS` | `statusCode` | `registry-system` | 2 | 출하 확정·취소 축 |
| `CD-SHIPMENT-TIME-SLOT` | `MORNING` `AFTERNOON` `NIGHT` | `SHIPMENT_TIME_SLOT` | `timeSlotCode` | `registry` | 4 | 공유계약 `G-32` 등록부 표의 근거 칸에서 옮겼다 |
| `CD-SHIPPING-INSPECTION-STATUS` | `HELD` `NOT_REQUIRED` `PASSED` `PENDING` `REJECTED` | — | `shippingInspectionStatusCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `ShipmentRequest`(`shipment-04제품출하`) |
| `CD-SOURCE-SYSTEM` | `ERP` `MES` | — | `sourceSystemCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `Department`(`mdm-기준정보`) |
| `CD-STATUS` | `CLOSED` `DRAFT` `PUBLISHED` `SCHEDULED` | — | `statusCode` | `enum` | 2 | 계약이 `enum` 으로 닫은 값 — `Notice`(`app-공통`) |
| `CD-STOCK-TRANSFER-REASON` | ⬜ | `STOCK_TRANSFER_REASON` | `reasonCode` | `registry` | 1 | 재고 이동 사유. ⭐ 「불량 반출이 몇 건인가」를 세려면 코드 축이어야 한다(§I-41 · `omf-mes#84`). 사유 코드 17자리가 이미 같은 형태다 — 스키마별 전용 그룹 + 고객이 늘림 |
| `CD-STOCK-TRANSFER-TYPE` | `NORMAL` `DEFECT_RETURN` | `STOCK_TRANSFER_TYPE` | `transferTypeCode` | `registry-system` | 3 | 재고 이동 유형. ⭐ `M-01-10` §4 가 「불량 반출일 때만 사유 칸을 연다」로 «동작»을 이 값에 걸었다 — 값이 늘면 화면 분기가 따라가지 못한다 |
| `CD-STORAGE-CONDITION` | `REFRIGERATED` `FROZEN` `ROOM_TEMPERATURE` `MOISTURE_CONTROLLED` `HAZARDOUS` | `STORAGE_CONDITION` | `storageConditionCode` | `registry` | 5 | 보관 조건. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-SUBSTITUTE-LOT-REASON` | `NO_LABEL` `LABEL_DAMAGED` `FORMAT_UNRECOGNIZED` `BULK_UNLABELED` `OTHER` | `SUBSTITUTE_LOT_REASON` | `substituteLotReasonCode` | `registry` | 2 | 대체 LOT 입력 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-TERMINAL-STATUS` | `RUNNING` `STOPPED` | `TERMINAL_STATUS` | `statusCode` | `registry-system` | 3 | 단말 가동 상태. ⛔ `isActive`(켬/끔 스위치)와 **다른 축** — 폐기는 재발급이 담당한다(`W-CO-06` §5-4) · 사용자 결정 2026-09-02 |
| `CD-TERMINAL-TYPE` | `POP` `MOBILE` | `TERMINAL_TYPE` | `terminalTypeCode` | `registry-system` | 2 | 단말 폼팩터. ⭐ 결정 16 이 확정한 아키텍처 축이다 — 고정 스테이션(POP)과 손에 드는 기기(MOBILE). 미결 대장이 「`terminal_type_code` 에 `MOBILE` 값이 있어야 한다」(`#64`)로 지목한 자리 |
| `CD-TOOL-TYPE` | `MOLD` `JIG` `OTHER` ⬜ | `TOOL_TYPE` | `toolTypeCode` | `registry` | 1 | 도구 유형. ⭐ `W-05-13` §3-3 이 「금형 / 지그 / 그 밖의 도구」로 확정했다 — `REQ-PR-0003` 「모든 도구」를 담는 축이고 테이블 이름(`mdm.mold`)은 바꾸지 않는다 |
| `CD-TRIGGER-TYPE` | `EVENT` `TIME_SCHEDULE` | — | `triggerTypeCode` | `enum` | 3 | 계약이 `enum` 으로 닫은 값 — `InterfaceDefinition` · `InterfaceDefinitionCreate`(`mdm-기준정보`) |
| `CD-VALUE-STATUS` | `AVAILABLE` `NOT_YET` `PARTIAL` | — | `valueStatusCode` | `enum` | 1 | 계약이 `enum` 으로 닫은 값 — `DashboardCard`(`app-공통`) |
| `CD-VARIANCE-REASON` | `MISPLACED` `DAMAGED_IN_TRANSIT` `SPILL` `COUNT_ERROR` `THEFT_LOSS` `EVAPORATION_LOSS` | `VARIANCE_REASON` | `varianceReasonCode` | `registry` | 4 | 재고실사·생산창고입고 차이 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-WAREHOUSE-TYPE` | `MATERIAL` `PRODUCT` `SPARE_PART` `GENERAL` | `WAREHOUSE_TYPE` | `warehouseTypeCode` | `registry` | 4 | 공유계약 `G-32` 등록부 표의 근거 칸에서 옮겼다 |
| `CD-WORK-CALENDAR-DAY-REASON` | `PUBLIC_HOLIDAY` `COMPANY_FOUNDING_DAY` `SUMMER_VACATION` `PLANNED_MAINTENANCE` `MAKEUP_WORKING_DAY` `OTHER` | `WORK_CALENDAR_DAY_REASON` | `reasonCode` | `registry` | 1 | 근무캘린더 예외일 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-WORK-ORDER-CANCEL-REASON` | `CUSTOMER_ORDER_CHANGE` `PLAN_CHANGE` `MATERIAL_SHORTAGE` `EQUIPMENT_FAILURE` `QUALITY_ISSUE` `OTHER` | `WORK_ORDER_CANCEL_REASON` | `reasonCode` | `registry` | 1 | WO 취소 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-WORK-ORDER-COMPLETION-VARIANCE-REASON` | `MATERIAL_SHORTAGE` `EQUIPMENT_FAILURE` `QUALITY_DEFECT` `PLAN_CHANGE` `OVER_PRODUCTION` `OTHER` | `WORK_ORDER_COMPLETION_VARIANCE_REASON` | `reasonCode` | `registry` | 1 | WO 완료 미달·초과 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-WORK-ORDER-STATUS` | `PLANNED` `CONFIRMED` `RELEASED` `IN_PROGRESS` `COMPLETED` `CLOSED` `SUSPENDED` `CANCELLED` | `WORK_ORDER_STATUS` | `statusCode` | `registry-system` | 2 | 작업지시 진행 상태 **8종**. ⭐ 결정 14 의 「8종」이 무엇인가가 닫혔다 — **진행불가 제외**(사용자 확정 2026-09-02). ⛔ 진행불가는 상태가 아니라 확정 게이트다 |
| `CD-WORK-ORDER-TYPE` | `NORMAL` `EMERGENCY` `REWORK` | `WORK_ORDER_TYPE` | `workOrderTypeCode` | `registry-system` | 3 | 작업지시 유형. ⭐ 계약이 값·그룹 이름을 이미 적었는데 **등록부에만 없었다** — 산문이라 포인터 검사기가 못 잡았다 · 사용자 결정 2026-09-02 |
| `CD-WORK-SESSION-EVENT-REASON` | `URGENT_ORDER_INTERRUPT` `EQUIPMENT_FAILURE` `TOOL_FAILURE` `MATERIAL_SHORTAGE` `MOLD_CHANGE` `QUALITY_ISSUE` `OTHER` | `WORK_SESSION_EVENT_REASON` | `reasonCode` | `registry` | 2 | 작업세션 이벤트 사유. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |
| `CD-WORK-SESSION-EVENT-TYPE` | `START` `STOP` `RESUME` `END` `CONTROL_OVERRIDE` | `WORK_SESSION_EVENT_TYPE` | `eventTypeCode` | `registry-system` | 3 | 작업세션 사건 유형. `omf-mes#198` 시드(`design/raw/…/2026-08-13-공통코드값목록-제안안`) |

### ⭐ 이 표가 증명하려는 것 셋

**① 값이 같아도 키는 다르다.** `documentTypeCode` 라는 «값 이름» 하나에 키가 **셋**이다 —
출력물 9값 · 물류 9값 · 취소 가능 3값. 사용자가 든 예(「검사 항목」과 「검증 항목」이 둘 다
`inspection` 이어도 키는 달라야 한다)의 실물이다.

⛔ **합치면 무엇이 깨지나** — 취소 오퍼레이션이 9값을 받으면 **취소할 수 없는 문서**(P/O·피킹 …)가
취소 목록에 뜬다. 조회 축이 3값만 받으면 **진행현황에 6종이 안 보인다.**

**② 같은 컬럼에 두 계열이면 키가 둘이다.** `equipmentTypeCode` 컬럼 하나에
`CD-EQUIPMENT-TYPE`(프레스·컨베이어)과 `CD-INSTRUMENT-TYPE`(캘리퍼스·게이지)이 착지한다.
`G-32` 가 이미 조항으로 세운 규칙이고(`#219`), **키가 그것을 표에서 보이게 한다.**

**③ ⚠ 반례 — 이름이 달라도 같은 종류면 «한 키»다.** `pmCycleUnitCode`(예방보전 주기 단위)와
`calibrationCycleTypeCode`(검교정 주기 단위)는 이름이 다르고 스펙 두 곳의 목록도 달랐지만
(`W-05-11` 「일/월/년」 · `W-05-12` 「일/주/월」) **둘 다 기간 단위**라 `CYCLE_TYPE` 하나다(`#188`).

⛔ **키 유일성 압력이 과분할을 부른다** — 그것을 막는 것이 이 행이다. 가르는 기준은
**「값이 같은 종류인가」**이지 「이름이 다른가」가 아니다.

---

## ⛔ 이 사전이 «세기»만 해서 찾아낸 것 — 형제 자리가 갈렸다

같은 이름의 코드가 어떤 자리에는 `enum`·포인터를 갖고 어떤 자리에는 **맨몸**으로 있다.
그 맨몸 자리를 보는 사람은 **「값 목록이 없다」로 읽는다.**

```
「형제 자리가 갈린」 코드   30 종
맨몸 자리                 120 개
  그중 쿼리 파라미터        52 개 (43%)
```

⭐ **패턴이 또렷하다 — 스키마에는 있는데 «쿼리 파라미터»에는 없다.**

| 코드 | 스키마 | 쿼리 |
| --- | --- | --- |
| `equipmentTypeCode` | 3자리 전부 포인터 | **1자리 맨몸** |
| `overallJudgmentCode` | 4자리 전부 포인터 | **3자리 전부 맨몸** |

⛔ **화면이 필터 선택칸을 못 만든다.** 응답 필드에 포인터가 있어도 **필터 UI 를 만드는 데는
쿼리 쪽이 필요하다.** 같은 형태를 `documentTypeCode` 에서 2026-09-02 에 고쳤다(쿼리 3자리).

### ⚠ 그런데 120 을 그대로 「고칠 것」으로 읽으면 안 된다 — 두 갈래다

| 갈래 | 무엇 | 예 | 어떻게 |
| :-: | --- | --- | --- |
| **(a)** | 같은 코드인데 어떤 자리만 값이 빠졌다 | `equipmentTypeCode` 쿼리 1 · `overallJudgmentCode` 쿼리 3 | **채운다** |
| **(b)** | 원래 «다른 코드»인데 이름이 같다 | `statusCode` 35 · `reasonCode` 15 · `targetTypeCode` 13 | **키를 가른다** |

⭐⭐ **사전이 없으면 이 둘을 구분할 수 없다.** 지금 검사기 셋 중 어느 것도 못 본다 —
`check-code-group-pointer` 는 가리킨 «이름»이 등록부 안인가만, `check-code-group-reachable` 은
화면이 그 그룹에 «닿는가»만 본다. **「형제끼리 갈렸는가」를 보는 검사기가 없다.**

⚠ **(b) 가 이 저장소의 오래된 물음이다** — `#145` 가 「`reasonCode` 값 목록을 정하자는 물음
자체가 틀렸다. **자리마다 다른 코드 그룹이어야 하고, 그러면 대상이 줄지 않고 늘어난다(1 → 15)**」
라 적은 자리이고, `#213` 이 `statusCode` 축을 따로 뺀 자리다. **키가 그 셈을 가능하게 한다.**

---

---

## ⛔ 형식이 한 번 틀렸다 — 「키·값 둘」로는 서지 않는다

첫 판은 열이 **다섯**이었고 「값」 자리에 **프로퍼티 이름**(`documentTypeCode`)을 적었다.
검사기를 돌리자 세 키가 **같은 9자리**를 봤다.

```
CD-PRINT-DOCUMENT-TYPE        사전 6   실물 9   ← 셋이 같은 것을 본다
CD-LOGISTICS-DOCUMENT-TYPE    사전 3   실물 9
CD-CANCELABLE-DOCUMENT-TYPE   사전 1   실물 9
```

⛔ **「어느 자리가 어느 키인가」를 기계가 판정 못 했다** — 그것이 이 사전의 핵심인데.

⇒ **값 열에 실제 코드 문자열을 담고**, 검사기가 자리의 `enum`·포인터와 **값으로** 대조하게
고쳤다. 그러자 갈렸다.

```
CD-PRINT-DOCUMENT-TYPE        사전 6   값있음 6   ✅
CD-LOGISTICS-DOCUMENT-TYPE    사전 3   값있음 3   ✅
CD-CANCELABLE-DOCUMENT-TYPE   사전 1   값있음 1   ✅
```

⭐ **이것이 테스트베드의 첫 소득이다** — 형식을 실물로 검증하지 않았으면
「키만 있으면 갈린다」는 잘못된 전제로 527자리에 퍼뜨렸을 것이다.

---

## 검증 결과 — 세운 기준 셋

| # | 기준 | 결과 |
| :-: | --- | :-: |
| ① | **키 유일성이 실물에서 성립하는가** — `documentTypeCode` 가 키 셋으로 갈리고 기계가 판정하는가 | ✅ **6·3·1 로 갈렸다.** ⚠ 단 «값»이 있어야 했다 |
| ② | **과분할이 안 일어나는가** — `CYCLE_TYPE` 두 자리가 한 키로 남는가 | ✅ `CD-CYCLE-TYPE` 이 두 프로퍼티 **6자리 전부**를 한 키로 잡았다 |
| ③ | **소유 열이 채워지는가** — 10개 전부 `A-16` 으로 판정 가능한가 | ✅ **10/10.** 「모르겠다」 0 |

### ⭐ 부산물 — 결손 5자리를 찾았다. 전부 «쿼리 파라미터»다

사전이 「이 코드는 N자리에 있다」고 **선언**하니 계약이 못 채운 자리가 드러났다.

| 키 | 선언 | 값 있음 | **맨몸** | 어디 |
| --- | :-: | :-: | :-: | --- |
| `CD-EQUIPMENT-TYPE` | 4 | 3 | **1** | `GET /mdm/equipments` |
| `CD-INSPECTION-OVERALL-JUDGMENT` | 7 | 4 | **3** | `GET /quality/inspection-results` · `…/defect-rate-trend` · `…/summary` |
| `CD-INSTRUMENT-TYPE` | 4 | 3 | **1** | 같은 자리(한 컬럼 두 계열) |

⛔ **화면이 필터 선택칸을 못 만든다.** 응답 스키마에는 포인터가 있어도 **필터 UI 를 만드는 데는
쿼리 쪽이 필요하다.** `documentTypeCode` 에서 2026-09-02 에 고친 것과 **같은 형태**다.

⭐ **이것을 잡은 것은 「검사기」가 아니라 「선언」이다** — 기존 검사기 셋은 「있는 것이 맞는가」만
보고 **「있어야 하는데 없는가」를 못 본다.** 사전이 그 물음을 세운다.

---

## 다음

1. ⬜ **위 결손 5자리를 채운다** — 별건. 쿼리 파라미터에 포인터를 단다
2. ⬜ **(b) 갈래로 넓힌다** — `statusCode` 54 · `reasonCode` 15 · `targetTypeCode` 13.
   이것이 `#213`(상태값 축)·`#145`(「`reasonCode` 자리가 15개」)가 이미 지목한 자리다
3. ⬜ **등록부 53그룹을 이 사전으로 이관** — 지금 조항 산문 + 검사기 상수 **2벌**이다
4. ⬜ 사전이 계약 653자리를 다 덮고 ④ 가 0 이 되면 **검사기를 게이트로 올린다**

⚠ **못 하는 것** — 물리 모델(`design/raw/`, 훅이 막는다)·프론트·서버 시드에는 강제력이 없다.
다만 지금 터지는 것의 대부분이 **우리 산출물끼리 어긋나는 것**이라 그것으로 충분하다.

⚠ **못 하는 것** — 물리 모델(`design/raw/`, 훅이 막는다)·프론트·서버 시드에는 강제력이 없다.
다만 지금 터지는 것의 대부분이 **우리 산출물끼리 어긋나는 것**이라 그것으로 충분하다.

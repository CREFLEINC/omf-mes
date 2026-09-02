# 코드 사전 — **테스트베드** (2026-09-02)

> ⚠ **이것은 시험판이다.** 계약 7벌의 코드 값 자리 **527개** 중 **35개**만 담았다.
> 형식이 실물과 맞는지 보려는 것이고, 맞으면 나머지로 넓힌다.
> ⛔ **아직 아무것도 고치지 않는다** — 이 사전은 «세기» 위한 것이다.

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

⛔ **새로 만드는 것이 아니다.** 공유계약 `G-32` 에 **53그룹**이 이미 등록돼 있고
`check-code-group-pointer.py` 가 게이트로 본다. 그런데 구멍이 셋이다.

| # | 구멍 |
| :-: | --- |
| ① | **사전이 이미 «둘»이고 손으로 맞춘다** — 조항 산문(3,079자 «한 줄») + 검사기 `REGISTRY` 상수. 검사기 자신이 「⛔ `REGISTRY` 만 늘려 초록을 만들지 마세요 — 조항이 정본입니다」라 경고한다 |
| ② | **세 갈래 중 «하나»만 담는다** — `A-16` 이 코드를 판별자·업무 코드·마스터안전형으로 가르는데, 등록부는 마스터안전형뿐이다. `enum` 으로 닫은 것(`documentTypeCode` 9종·`approvalTypeCode` 8종 …)은 **사전이 없다** |
| ③ | **키가 없다** — 그룹 «이름»이 곧 키라 산문 속에서 그것이 사전 항목인지 알 수 없다 |

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

| 값 | 뜻 | 계약에서 |
| --- | --- | --- |
| `enum` | **설계가 정한다** | 계약이 값 목록을 갖는다. ⛔ 등록부에 안 올린다 |
| `registry` | **고객이 운영 중에 정한다**(`G-31` 마스터안전형) | 계약은 `codeGroupCode=` 포인터만. 등록부(`G-32`)에 오른다 |
| `derived` | **서버가 파생한다** | 화면이 안 보낸다 |

---

## 사전 — 10키 / 35자리

⛔ **열이 여섯이다 — 「키·값」 둘로는 서지 않는다.** 테스트베드가 그것을 실물로 증명했다(§ 아래 「형식이
한 번 틀렸다」). **값**은 실제 코드 문자열이고(`enum` 갈래) 또는 그룹 이름이며(`registry` 갈래),
**프로퍼티**는 계약이 부르는 이름이라 **중복한다.**

| 키 | 값 | 프로퍼티 | 소유 | 자리 | 근거 |
| --- | --- | --- | :-: | :-: | --- |
| `CD-PRINT-DOCUMENT-TYPE` | `MATERIAL_LOT_LABEL` `GOODS_ISSUE_QR` `PRODUCTION_LOT_LABEL` `IDENTIFICATION_TAG` `PACKING_LABEL` `DELIVERY_LABEL` `CERTIFICATE_OF_ANALYSIS` `TOOL_LABEL` `LOCATION_LABEL` | `documentTypeCode` `supportedDocumentTypeCodes` | `enum` | 6 | 출력물 종류. `app-공통.json` — `omf-mes#145` · `22c08f5` · 요구서 `app공통출력물` §3-8 |
| `CD-LOGISTICS-DOCUMENT-TYPE` | `PURCHASE_ORDER` `INBOUND_RECEIPT` `GOODS_RECEIPT` `MATERIAL_ISSUE_REQUEST` `PICKING_ORDER` `STOCK_TRANSFER` `SUBCONTRACT_ISSUE` `SUBCONTRACT_RECEIPT` `GOODS_ISSUE` | `documentTypeCode` | `enum` | 3 | 물류 문서 종류. `logistics-01자재창고.json` — `#351` · `06942be` |
| `CD-CANCELABLE-DOCUMENT-TYPE` | `INBOUND_RECEIPT` `GOODS_RECEIPT` `GOODS_ISSUE` | `documentTypeCode` | `enum` | 1 | 취소할 수 있는 문서. 같은 계약 · 「자리마다 닫는다」 |
| `CD-APPROVAL-TYPE` | `GOODS_ISSUE_DISPOSAL` `INVENTORY_ADJUSTMENT` `PURCHASE_ORDER` `INBOUND_RECEIPT_CANCEL` `GOODS_RECEIPT_CANCEL` `GOODS_ISSUE_CANCEL` `SHIPMENT_CANCEL` `IQC_SKIP` | `approvalTypeCode` | `enum` | 5 | 승인 유형 8값. `#336` · 사용자 확정 2026-09-01 |
| `CD-GOODS-ISSUE-DESTINATION-TYPE` | `LOCATION` `PARTNER` `DISPOSAL_SITE` | `destinationTypeCode` | `enum` | 2 | 출고 도착지. ⚠ 계약 `enum` 에 `null` 이 함께 있다(nullable). `#337` |
| `CD-INSPECTION-OVERALL-JUDGMENT` | `INSPECTION_RESULT_OVERALL_JUDGMENT` | `overallJudgmentCode` | `registry` | 7 | 합격·불합격·**보류** 3값. `#179` |
| `CD-INSPECTION-MEASUREMENT-JUDGMENT` | `INSPECTION_MEASUREMENT_JUDGMENT` | `judgmentCode` | `registry` | 2 | 합격·불합격 **2값**. `#179` |
| `CD-EQUIPMENT-TYPE` | `EQUIPMENT_TYPE` | `equipmentTypeCode` | `registry` | 4 | 설비 계열. `#186` · 통지 `client#415` |
| `CD-INSTRUMENT-TYPE` | `INSTRUMENT_TYPE` | `equipmentTypeCode` | `registry` | 4 | 계측기 계열. **같은 컬럼에 두 계열**(`G-32` · `#219`) · 통지 `client#404` |
| `CD-CYCLE-TYPE` | `CYCLE_TYPE` | `pmCycleUnitCode` `calibrationCycleTypeCode` | `registry` | 6 | 기간 단위. ⭐ **반례** — 아래 참조 |

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
| `CD-INSPECTION-OVERALL-JUDGMENT` | 7 | 4 | **3** | `GET /quality/inspection-results` · `…/defect-rate-trend` · `…/summary` |
| `CD-EQUIPMENT-TYPE` | 4 | 3 | **1** | `GET /mdm/equipments` |
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

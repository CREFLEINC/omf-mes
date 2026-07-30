# -*- coding: utf-8 -*-
"""04-통합-IA.md -> 도식본 단일 HTML (외부 asset 0).

선례: uiux/2026-07-25-화면목록-IA/build-도식본.py (도식 6종·색 부호화·다크모드).
개선 3가지:
  ① **md 직접 파싱** — 선례는 중간 JSON 을 입력으로 받아 재현이 불가했다.
  ② **조용한 실패 제거** — 선례 chip() 은 미등록 ID 를 빈 문자열로 삼켜, 결번 W-03-04 가
     STAGES·TREE 에 살아 있는데도 렌더에서 사라져 검출되지 않았다. 여기서는 예외를 던진다.
  ③ **빌드 assert** — 전건 109·프로그램·도메인·신뢰도·유형 교차 계수가 어긋나면 생성 중단.

부호화 규율 (색 채널을 하나의 의미에만):
  · 색 = 프로그램 3종 전용 (웹 #2F6FED · POP #F2994A · 모바일 #27AE60 — 배지 정책 색, 04 §2-2)
  · 신뢰도 = 형태 전용 (실선 확정 / 점선 추정 / 이중 점선 미정 + 텍스트 병기)
  · 변동 = 기호 전용 (신설 ✦ / 결번 취소선 / 이관 ↗ / 격하 ↓)

사용법: python3 build-04-ia-도식본.py
"""
import io, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, '04-통합-IA.md')
DST  = os.path.join(HERE, '04-통합-IA-도식본.html')

SNAPSHOT = '2026-07-30'          # 미결·이월 스냅샷 기준일 (§7·§8 은 며칠 단위로 바뀐다)

# ════════════════════════════════════════════════════════════════════════════
# 1. 정본 파싱 — 화면 109건
# ════════════════════════════════════════════════════════════════════════════

ROW = re.compile(r'^\|\s*`([WPM]-(?:CO|\d{2})-\d{2})`\s*\|(.+)$')

def parse_rows(md):
    """§3-2·§4-2·§5-2 인벤토리 표만 읽는다.
    ⚠ 셀 수 6개 이상 조건이 필수 — §6-2 삭제 표·§7 미결 표가 같은 백틱 ID 패턴을
    3셀로 쓰기 때문에, 조건을 빼면 결번이 화면으로 섞여 들어온다."""
    seg = re.search(r'## §3\.(.*?)## §6\.', md, re.S)
    rows, seen = [], set()
    for ln in seg.group(1).split('\n'):
        m = ROW.match(ln)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split('|')]
        if len(cells) < 6:
            continue
        sid = m.group(1)
        if sid in seen:
            raise SystemExit('중복 행: ' + sid)
        seen.add(sid)
        rows.append({
            'id': sid, 'name': cells[0], 'type': cells[1], 'actor': cells[2],
            'data': cells[3], 'conf': cells[4], 'why': cells[5],
            'prog': {'W': 'web', 'P': 'pop', 'M': 'mob'}[sid[0]],
            'dom': sid.split('-')[1],
        })
    return rows

MD   = io.open(SRC, encoding='utf-8').read()
ROWS = parse_rows(MD)
BY   = {r['id']: r for r in ROWS}

# ════════════════════════════════════════════════════════════════════════════
# 2. 편집 판단으로 만든 구조 — 정본에 「업무 단계 열」이 없으므로 파생이다
#    선례(build-도식본.py STAGES/BANDS)를 계승하고 아래 3가지만 바꿨다:
#      · 결번 W-03-04 제거 (v1.3 통합 — 선례에 잔존해 있었다)
#      · 「입하」를 정본 대흐름대로 입하(S2) / 수입검사(S3) / 입고(S4) 3단계로 분리
#      · 근거가 명확한 이동 3건만 적용 (아래 MOVES) — 근거가 약한 이동 7건은 §관찰로만 남긴다
# ════════════════════════════════════════════════════════════════════════════

MOVES = [
 ('W-01-10', '수입검사 → 입하·입고(G/R)',
  'WF01 S4 입고 화면 — 정본이 M-01-02·P-01-01 과 한 줄에 열거하고 단말을 「모바일+POP+관리웹」으로 묶는다 (05 §3.1 S4·§9.1 01·S4)'),
 ('W-02-05', '출하 → 생산 실행',
  'W/O 마감·ERP 실적 송신은 WF02 S12(02 메인 축 마지막) — 04 출하 흐름(S3~S7)과 연결이 없다 (05 §4.1 S12)'),
 ('M-04-04', '출하 → 제품검사·포장·제품입고',
  'WF04 S1 제품입고(제품LOT 형성) 화면 — 정본 대흐름에서 「완제품 입고」는 OQC·출하보다 앞이다 (05 §6.1 S1)'),
]

# 순방향 축 — 9단계 (각 단계: 키, 라벨, 도메인, WF 근거, 레인)
STAGES = [
 ('입하', '입하', '01', 'WF01 S1·S2 · 01-S-A/B',
  {'web': ['W-01-09', 'W-01-03', 'W-01-11'], 'pop': [], 'mob': ['M-01-01', 'M-01-06']}),
 ('수입검사', '수입검사 (IQC)', '01', 'WF01 S3 · 01-S-C',
  {'web': ['W-01-01', 'W-01-02'], 'pop': [], 'mob': []}),
 ('입고', '입고 (G/R) · Release', '01', 'WF01 S4',
  {'web': ['W-01-10'], 'pop': ['P-01-01'], 'mob': ['M-01-02']}),
 ('적치', '적치 · 보관', '01', 'WF01 S5·S6 · 01-S-D',
  {'web': ['W-01-07'], 'pop': [], 'mob': ['M-01-04', 'M-01-05', 'M-01-07']}),
 ('출고', '출고 · 투입', '01·02', 'WF01 S7·S12 · 01-S-E/F',
  {'web': ['W-02-10'], 'pop': ['P-01-02'], 'mob': ['M-01-08', 'M-01-09', 'M-01-12']}),
 ('계획', '생산 계획 · 지시', '02', 'WF02 S1~S4 · 02-S-B/C/D',
  {'web': ['W-02-01', 'W-02-02', 'W-02-03', 'W-02-04', 'W-02-06', 'W-02-07'], 'pop': [], 'mob': []}),
 ('실행', '생산 실행', '02', 'WF02 S5~S12 · 02-S-A/I',
  {'web': ['W-02-08', 'W-02-05'], 'pop': ['P-CO-01', 'P-02-01', 'P-02-02', 'P-02-03', 'P-02-04',
                                          'P-02-06', 'P-02-10', 'P-02-11', 'P-02-12'],
   'mob': ['M-02-01', 'M-02-02']}),
 ('검사포장', '제품검사 · 포장 · 제품입고', '02·03·04', 'WF02 S8·S10 · WF03 S3~S6 · WF04 S1',
  {'web': ['W-03-01', 'W-03-02', 'W-03-03', 'W-03-09', 'W-04-03'],
   'pop': ['P-02-13', 'P-02-05', 'P-02-07', 'P-02-08', 'P-02-09', 'P-04-04', 'P-04-03'],
   'mob': ['M-04-03', 'M-04-04']}),
 ('출하', '출하 · 마감', '04', 'WF04 S3~S7',
  {'web': ['W-04-01', 'W-04-02', 'W-04-04', 'W-04-05'], 'pop': ['P-04-01', 'P-04-02'],
   'mob': ['M-04-01']}),
]

# 흐름 밖 — 역흐름·횡단·상시
BANDS = [
 ('예외 · 역흐름', '반품 · 폐기 · 재고조정 · 재고이동 · 실사',
  'WF01 S8~S11 · WF04 S9·S10 · 01-S-G/H/I · 04-S-C',
  {'web': ['W-01-04', 'W-01-12', 'W-01-05', 'W-01-06', 'W-04-06', 'W-04-11', 'W-04-07', 'W-04-10'],
   'pop': [], 'mob': ['M-01-10', 'M-01-11']}),
 ('설비 · 툴 (05)', '점검 · 보전 · 비가동 · 계측 — 생산 실행에 게이트로 걸린다',
  'WF05 S1~S9 · 05-S-A~E',
  {'web': ['W-05-01', 'W-05-02', 'W-05-03', 'W-05-04', 'W-05-05', 'W-05-06', 'W-05-07', 'W-05-08',
           'W-05-09', 'W-05-10', 'W-05-11', 'W-05-12', 'W-05-13'],
   'pop': ['P-05-01', 'P-05-02'], 'mob': ['M-05-01', 'M-05-02']}),
 ('기준정보 · 연계 (06)', '마스터 · Rev · I/F — 전 단계의 입력을 공급한다',
  'WF06 S1~S9 · 06-S-A~D',
  {'web': ['W-06-01', 'W-06-02', 'W-06-03', 'W-06-04', 'W-06-05', 'W-06-06', 'W-06-07', 'W-06-08',
           'W-06-09', 'W-06-10', 'W-06-11', 'W-06-12', 'W-06-13'], 'pop': [], 'mob': []}),
 ('공통 (CO)', '계정 · 권한 · 알림 · 대시보드 · 설정 — 셸에 상시',
  '§3-1 시스템/공통 · §5-1 진입',
  {'web': ['W-CO-01', 'W-CO-02', 'W-CO-03', 'W-CO-04', 'W-CO-05', 'W-CO-06', 'W-CO-08'],
   'pop': [], 'mob': ['M-CO-01']}),
 ('조회 (도식 앵커 밖)', '전 도메인 — 비도식 근거로 도출된 조회 화면',
  '§9-2 비도식 근거 규칙 v0.2',
  {'web': ['W-03-05', 'W-04-08'], 'pop': [], 'mob': []}),
]

# 단말 전환 — ① 스택(배지 정본 근거) ② 단계 경계(계산) ③ 미결
STACKS = [
 ('04-S-D', '재구성 스캔 → 발번 · 라벨 인쇄', [('M-04-03', 'mob'), ('P-04-04', 'pop')],
  '§2-3 2단말 스택 · §5-2 M-04-03 「모바일+POP 스택」'),
 ('05-S-B', '고장 보고 → 처리 · 보전 지시', [('M-05-02', 'mob'), ('W-05-04', 'web')],
  '§2-3 2단말 스택 · §3-2 W-05-04 근거 열'),
 ('05-S-D', '비가동 수집 → 집계 · 조회', [('P-05-02', 'pop'), ('W-05-08', 'web')],
  '§2-3 2단말 스택 · §3-2 W-05-08 근거 열'),
]
SHIFT_NOTES = [
 ('S4 입고 = 3단말이 한 단계에 서는 유일 지점',
  '모바일 LOT 스캔(M-01-02) · POP 발번·라벨(P-01-01) · 웹 입고 확정·Release·G/R 송신(W-01-10) — 정본이 단말 필드에 「모바일 + POP + 관리웹」이라 적은 유일한 단계'),
 ('판정 = 웹 · 수집 = 현장, 예외는 딱 하나',
  'IQC(웹) · OQC(웹) 대비 **PQC 만 POP**(P-02-13) — 근거는 배지 정책 2 + 결정 12'),
 ('스택 3건이 전부 「현장 수집 → 사무 처리」 패턴',
  '04-S-D 재구성 · 05-S-B 고장 · 05-S-D 비가동 — 같은 지점에 두 단말이 서므로 셸 간 레코드 공유 설계가 필요하다(§7-4 파생 확인 사항)'),
 ('⚠ 미결 경계 1건',
  'M-01-02(자재LOT 번호 스캔·등록) ↔ P-01-01(자재LOT 발번·라벨 인쇄) — 입하 진입 「부착 여부」 분기 2곳 중복이 캔버스 정리 대기라 두 화면의 경계가 유동(§7-5)'),
]

# v1.3 변동 — 04 §6-2·§6-3
GONE = [
 ('W-01-08', '위치 확인 모니터링', 'web', 'del',
  [('W-01-07', '재고 현황·상태 조회 — 위치별 분포 뷰')],
  'REQ-PR-0005 는 「자재 LOT 적재(보관) 위치 정보 관리」 요구 — 모니터링 대시보드 요구가 아니다'),
 ('W-02-09', '생산 현황·비가동 알람 대시보드', 'web', 'del',
  [('W-CO-03', '알람 → 알림센터'), ('W-02-08', '생산 현황·실적 집계'), ('W-CO-05', '일일 생산실적')],
  'REQ-PR-0016 은 「알람」 요구 — 알람 채널은 SNS + 알림센터로 이미 확정(QA #24)'),
 ('W-03-08', '품질 대시보드·불량 발생 알람', 'web', 'del',
  [('W-CO-03', '알람 → 알림센터'), ('W-03-05', '불량률·불량코드 분포 집계 뷰')],
  '동상 — 「알람」을 대시보드로 바꿔 읽은 결과'),
 ('W-04-09', '출하 현황 모니터링 대시보드', 'web', 'del',
  [('W-04-02', '출하 예정 목록'), ('W-04-08', '완제품 재고 조회')],
  'QA #21 「현행 모니터링 없음 · 추후 고객 요구」 = 아직 요구가 아니다'),
 ('W-05-14', '설비·툴 대시보드', 'web', 'del',
  [('W-CO-05', '통합 대시보드'), ('W-05-08', '가동률/OEE'), ('W-05-02', 'PM 도래')],
  'REQ-PR-0036 하나가 화면 둘을 정당화하지 못한다'),
 ('W-03-04', '변경이력 조회', 'web', 'merge',
  [('W-03-01', 'Lot Status 현황·변경이력 조회')],
  'N6 현재 / N7 이력 = 같은 엔티티의 현재와 과거(결정 10) — 단 §8-1 요건 2종(이력 검색 모드·권한 분리)이 조건'),
 ('W-CO-07', '다국어 환경설정', 'web', 'demote',
  [('셸 전역 컨트롤', '관리웹 헤더 한/베 토글')],
  'REQ-PR-0012 는 「한/베 지원」이지 설정 화면 요구가 아니고 「사용자 환경설정」 엔티티가 실측 0건'),
 ('W-03-06', '불량·부적합 판정·폐기 품의', 'web', 'del',
  [('W-03-02', '판정 → 검사 화면'), ('W-01-06', '품의 → 도메인 품의 화면')],
  'v1.2 — 03 co-locate 위반 · 소유 엔티티 0'),
 ('W-03-07', 'SPC 관제 대시보드', 'web', 'move',
  [('Analytics (OMF-AI)', '단계 이관 — 추적 유지')],
  'v1.2 — 결정 11 이 Analytics 단계로 이연 명시. 삭제가 아니라 **이관**'),
 ('M-01-03', 'IQC 대상 LOT 스캔', 'mob', 'merge',
  [('W-01-01', 'IQC 수입검사·판정 — 01-S-C 전 구간')],
  'v1.2 — 01-S-C 전체가 IQC 담당자·웹으로 확정(리더 결정)'),
 ('M-04-02', '피킹 대상 목록', 'mob', 'merge',
  [('M-04-01', '제품LOT 피킹 스캔')],
  'v1.2 — 목록(Wallet) = 진입 경로 기준 · 작업 중 대상 선택이라 흡수'),
]
NEW3 = [
 ('M-04-04', 'WF04 S1 제품입고 = 제품LOT genealogy 시작점 공백(적대 검증 N2). 모바일 근거 3종 — Actor 완제품창고담당 · Action 적치 · Input 인식표 QR'),
 ('W-06-13', '개념모델에 「검사정책」 엔티티 실재 — MES 정본 엔티티는 관리 화면 1개(비도식 근거 규칙 기준 A)'),
 ('W-CO-08', 'REQ-PR-0036 「현장 공장 및 창고 레이아웃 배치」 + 레이아웃 엔티티 실재'),
]

# 차단 원인 → 영향 화면 (04 §7)
BLOCKERS = [
 ('회신 E-3', '판정유형 값 목록 (한도승인·특채·폐기)', '고객 회신',
  ['W-03-09', 'W-01-02', 'W-06-04'],
  '존치 3건(노드 587:6776·6779·6782) — 상태 개수가 바뀌므로 W-03-09 분리 여부·W-01-02 범위를 지금 정할 수 없다. 회신 시 3상태 도식화 + 관리웹 칩 3개 부착까지 연쇄', '='),
 ('회신 E-4', '기타출고 계정 항목', '고객 회신', ['W-04-10'],
  '화면의 존재·범위 자체가 유동 — 신뢰도 **미정**', '?'),
 ('회신 E-1', '연계 실패·알람 상황 유형 목록', '고객 회신', ['W-06-10'],
  '화면의 존재·범위 자체가 유동 — 신뢰도 **미정**', '?'),
 ('고객사 협의', 'LOT 수량 정정 (부분 입고 허용 여부 · 노드 226:5738)', '고객사 협의', [],
  '부분 입고 허용이 협의 사항이라 관련 결정 전부 유보 — 화면 미특정', '='),
 ('H/W 단말 정리', '단말기 종류 · 설치 위치 · 수량', '고객사 정리', ['W-CO-06'],
  'POP 설치위치(트랙 H) 의존 — W-CO-06 은 도식 배지·앵커 없는 인프라 설정 추정', '='),
 ('이슈 #44', '04 SC4 도식 결함 (인접 행위 노드 0개)', 'docs 이슈', ['W-04-07'],
  'W-04-07 이 이 공백 위에 서 있다 — 도식 수정 후 재판정', '='),
 ('이슈 #40', 'FigJam 캔버스 배지 3칩 반영 (66 → 68칩)', 'docs 이슈', [],
  '정본 65배치/68칩 ↔ 캔버스 66칩 차이 — 화면 수 무영향(정합 작업)', '='),
 ('이슈 #53', '「외주」 문서 간 경계 (WF01 ↔ WF04)', 'docs 이슈', ['M-01-01', 'M-04-04'],
  '외주 수입검사 판정 화면 재사용 여부 · 입하↔제품입고 경계', '='),
 ('이슈 #54', '작업조(Shift/Crew) 마스터 소유', 'docs 이슈', ['W-06-06'],
  'ERP 「조직」 포함이면 W-06-06 이 받고(변동 0), MES 정본이면 화면 **신설(+1)**', '+'),
 ('H6 재확인', '기포장품 스킵 경로의 납품라벨 부착 절차', '도식 확인', ['W-04-01'],
  '도식스펙-04 [확인] 7 이 「붙인다」로 풀리면 G-04-01 흡수 판정이 뒤집힌다', '='),
]

# 이월 요건 — 04 §8 (상세 스펙 단계에서 반드시 반영)
CARRY = [
 (['W-03-01', 'W-CO-02'], '① 이력 검색 모드(기간·판정유형·행위자) ② 권한 분리(감사 조회=품질책임자 범위 제한)', 'v1.3 통합 조건 · 결정 10'),
 (['W-03-05', 'W-02-08', 'W-01-07'], '집계 뷰 3건 — 불량률·불량코드 분포 / 생산 실적 / 위치별 분포', '대시보드 삭제분 기능 유실 방지'),
 (['W-05-13', 'W-06-07'], 'QR·Location 라벨 **이미지 생성**까지 (물리 인쇄는 범위 밖)', '리더 확정 「마스터 라벨 = 이미지 생성까지」'),
 (['W-04-01'], '「지시서 없이 단독 생성」 모드', '긴급·예외 경로'),
 (['P-02-05', 'P-02-07'], '병합 검토 — 발행 시점이 같다 (?)', '§8-6 상세 스펙 단계 판단'),
 (['W-01-01'], '웹 화면에 바코드 스캐너 입력 — IQC 공간 PC/스캐너 H/W 미반영', '이슈 #41 계열'),
 (['P-02-02'], '작업 통제 3단계(차단/경고/미적용) — 설정처는 원문 미확정', 'QA #9'),
 (['W-02-02', 'W-02-04'], '생산LOT 분할 지정 UI — W/O 편성·진행 중 W/O 양쪽에서 가능', '러닝체인지 리더 확정'),
 (['W-06-05', 'W-06-06'], '마스터 한/베 명칭 편집 (다국어 3성격 중 ①)', 'REQ-PR-0012'),
 (['W-03-02'], '판정 유형 확장 여지 — 회신 E-3 후 3상태 추가', '§7-1'),
 (['M-04-01'], 'FEFO/FIFO 강제·선택 옵션', 'QA #28'),
 (['W-04-04'], '출하 후 ERP 반영(PGI 전표) 송신 on/off', 'QA #6'),
 (['W-01-02', 'W-02-07', 'P-02-12', 'W-04-05'], '긴급 경로 = 정상 화면 재사용 + 긴급 플래그 (신설 아님)', '매핑 4단계 확정'),
 (['W-CO-03'], '알림 수신처 단일화 — 대시보드 5건 삭제의 근거', 'QA #24'),
 (['W-CO-01', 'P-CO-01', 'M-CO-01'], '인증 3계층 — 계정 로그인 / 사번 경량(로그인 생략) / 계정+기기 등록', '결정 16 · POP인증 §6'),
 ([], '조회 화면의 적정 표시 범위 — 집계 뷰 요건이 붙은 조회 화면 공통 (전역 원칙)', '§8-16'),
]

# 분할·병합 판정 실례 — 04 §9-1 규칙 + §6 변동 실례
PAIRS = [
 ('단말이 바뀐다', '배지 정본이 기계적 정답 — 같은 지점에 두 단말이 서면 두 화면',
  [(('M-04-03', 'P-04-04'), '⇄', '04-S-D 재구성 스캔(모바일) / 발번·라벨 인쇄(POP)'),
   (('M-05-02', 'W-05-04'), '⇄', '05-S-B 고장 보고(모바일) / 처리·보전 지시(웹)'),
   (('P-05-02', 'W-05-08'), '⇄', '05-S-D 비가동 수집(POP) / 집계·조회(웹)')]),
 ('저장 엔티티가 다르다', '관리웹 절단 = 저장 엔티티 — 순환 정의였던 「메뉴 항목이면 독립」을 교체',
  [(('W-01-03', 'W-01-11'), '⇄', '초과 입하 분리 / 신규 P/O 등록(ERP 전표+승인 마커·저장 엔티티 상이)'),
   (('W-01-04', 'W-01-12'), '⇄', '재고실사 / 재고조정(ERP 조정 전표)')]),
 ('작업이 끊긴다', '실물 작업 개입 + 전후가 다른 데이터면 분리 · 같은 레코드를 이어 완성하면 1화면',
  [(('W-04-06', 'W-04-11'), '⇄', '반품·클레임 입고 / 재고 재등록 — 사이에 03 판정·재작업이 낀다')]),
 ('진입 경로가 다르다', '목록(Wallet) = 조회 목적 직접 진입이면 독립 · 작업 중 대상 선택이면 흡수',
  [(('M-04-02', 'M-04-01'), '⊕', '피킹 대상 목록 → 제품LOT 피킹 스캔에 흡수(작업 중 선택)')]),
 ('라벨은 발행 시점', '「부착」은 화면 밖 — 발행 시점이 같으면 한 화면 후보',
  [(('P-02-05', 'P-02-07'), '?', '인식표 발행 / LOT 라벨 출력 — 발행 시점이 같아 **병합 검토 중**(§8-6)')]),
 ('전부 충족 → 한 화면', '단말·엔티티·끊김·진입이 모두 같으면 하나로 묶는다',
  [(('M-01-03', 'W-01-01'), '⊕', '01-S-C 전 구간이 IQC 담당자·웹으로 확정 → 흡수'),
   (('W-03-04', 'W-03-01'), '⊕', '같은 엔티티의 현재와 과거(결정 10) → 통합, 단 요건 2종 필수')]),
]

# 인증·권한 — 04 §2-1·§3-2·§4-2·§5-2
AUTH = [
 ('web', '관리웹', 'W-CO-01', '계정 로그인', ['온라인 전제', '계정·역할 기반', '판정·승인 행위의 감사 기록 주체']),
 ('pop', 'POP', 'P-CO-01', '사번 경량 인증', ['**로그인이 아니다** — 작업 시작 전 사번만 입력(REQ-PR-0023)',
                                        '단말 토큰 + 사번 귀속 3층 분리(POP인증 §6-①②③)', '실적 귀속 태깅']),
 ('mob', '모바일', 'M-CO-01', '계정 로그인 + 기기 등록', ['BLE 스캐너 페어링 · 언어 선택',
                                                 '단말 인증 말단 확정 = POP 과 동일(POP인증 §6-③)']),
]
GATES = [('W-01-02', '권한자(MES 권한 보유 관리자)'), ('W-03-09', '품질책임자·권한자'),
         ('W-01-06', '품의 결재권자'), ('W-04-10', '품의 결재권자')]
SHELL = [
 ('web', '관리웹 셸 전역 컨트롤', ['한/베 언어 토글 — 구 `W-CO-07` 격하 (페이지가 아니라 버튼)',
                            '알림 배지 — `W-CO-03` 미확인 건수']),
 ('pop', 'POP 셸 상태바', ['오프라인·미동기 N건 표시(결정 17)', '한/베 언어 토글']),
 ('mob', '모바일 셸', ['언어 선택 — `M-CO-01` 진입에 포함']),
]

# IA 3모델 — 04 §3-1·§4-1·§5-1
TREE = [
 ('기준정보', [('마스터', ['W-06-01', 'W-06-05', 'W-06-06', 'W-06-07', 'W-06-08', 'W-06-11']),
            ('품질 기준', ['W-06-02', 'W-06-03', 'W-06-04', 'W-06-13']),
            ('연계(I/F)', ['W-06-09', 'W-06-12', 'W-06-10'])]),
 ('생산', [('계획·지시', ['W-02-01', 'W-02-02', 'W-02-03', 'W-02-04', 'W-02-07', 'W-02-06', 'W-02-10']),
         ('마감·모니터링', ['W-02-05', 'W-02-08'])]),
 ('품질', [('Lot Status', ['W-03-01', 'W-03-02', 'W-03-03', 'W-03-09']),
         ('검사·불량', ['W-03-05'])]),
 ('자재/창고', [('입하·검사', ['W-01-09', 'W-01-01', 'W-01-10', 'W-01-02', 'W-01-03', 'W-01-11']),
             ('재고·출고', ['W-01-07', 'W-01-04', 'W-01-12']),
             ('반품·폐기', ['W-01-05', 'W-01-06'])]),
 ('출하', [('출하 지시·확정', ['W-04-01', 'W-04-02', 'W-04-03', 'W-04-04', 'W-04-05']),
         ('반품·재고', ['W-04-06', 'W-04-11', 'W-04-07', 'W-04-08', 'W-04-10'])]),
 ('설비/툴', [('툴 관리', ['W-05-01', 'W-05-02', 'W-05-03', 'W-05-13']),
            ('설비 보전', ['W-05-04', 'W-05-05', 'W-05-06', 'W-05-12']),
            ('비가동·계측', ['W-05-08', 'W-05-09', 'W-05-07', 'W-05-10', 'W-05-11'])]),
 ('시스템/공통', [('계정·권한', ['W-CO-01', 'W-CO-02']), ('알림·공지', ['W-CO-03', 'W-CO-04']),
              ('설정', ['W-CO-06', 'W-CO-08']), ('경영 대시보드', ['W-CO-05'])]),
]
POP_MODES = [
 ('0. 진입 (공통 셸)', ['P-CO-01', 'P-02-01'], '사번 입력 → 내 W/O 목록'),
 ('1. 작업 전 점검 게이트', ['P-02-02'], '점검 미완이면 생산 차단(WF05 S3)'),
 ('2. 생산 실행 모드', ['P-02-03', 'P-02-04', 'P-02-13', 'P-02-05', 'P-02-06', 'P-02-07',
                   'P-02-10', 'P-02-11', 'P-02-12'], '투입 스캔 → 실적 → PQC → 라벨·인식표 → 예외·긴급'),
 ('3. 포장 · 출하 모드 (02·04)', ['P-02-08', 'P-02-09', 'P-04-01', 'P-04-02', 'P-04-04', 'P-04-03'],
  '생산 포장(02 S10) ↔ 출하 P&P(04 S6)'),
 ('4. 창고 스테이션 모드 (01)', ['P-01-01', 'P-01-02'], '자재LOT 발번·라벨 / 출고 QR'),
 ('5. 설비 · 현장 수집 모드 (05)', ['P-05-01', 'P-05-02'], '타발수 · 비가동 수집'),
]
TILES = [
 ('📦', '입하', ['M-01-01', 'M-01-02', 'M-01-06']), ('📥', '적치', ['M-01-04', 'M-01-05', 'M-01-07']),
 ('📤', '피킹 / 출고', ['M-01-08', 'M-01-09']), ('♻️', '재생재', ['M-01-12']),
 ('🔀', '이동', ['M-01-10']), ('🧮', '실사', ['M-01-11']),
 ('🏭', '생산 이동 / 수리 (02)', ['M-02-01', 'M-02-02']),
 ('🚚', '출하 스캔 (04)', ['M-04-01', 'M-04-03', 'M-04-04']), ('🛠', '설비 (05)', ['M-05-01', 'M-05-02']),
]
MOB_ENTRY = ['M-CO-01']

# ════════════════════════════════════════════════════════════════════════════
# 3. 빌드 assert — 어긋나면 생성 중단
# ════════════════════════════════════════════════════════════════════════════

VACATED = {r[0] for r in GONE}          # 결번 11건

def die(msg):
    raise SystemExit('빌드 중단 — ' + msg)

def collect(groups):
    out = []
    for g in groups:
        for k in ('web', 'pop', 'mob'):
            out += g[-1].get(k, [])
    return out

flow_ids = collect(STAGES) + collect(BANDS)
tree_ids = [s for _, gs in TREE for _, ids in gs for s in ids]
pop_ids  = [s for _, ids, _ in POP_MODES for s in ids]
tile_ids = MOB_ENTRY + [s for _, _, ids in TILES for s in ids]

if len(ROWS) != 109: die('화면 %d건 (109 아님)' % len(ROWS))
c = Counter(r['prog'] for r in ROWS)
if (c['web'], c['pop'], c['mob']) != (68, 22, 19): die('프로그램 계수 %s' % dict(c))
d = Counter(r['dom'] for r in ROWS)
if dict(d) != {'01': 24, '02': 24, '03': 5, '04': 17, '05': 17, '06': 13, 'CO': 9}: die('도메인 계수 %s' % dict(d))
f = Counter(r['conf'] for r in ROWS)
if (f['확정'], f['추정'], f['미정']) != (82, 25, 2): die('신뢰도 계수 %s' % dict(f))
if sum(Counter(r['type'] for r in ROWS).values()) != 109: die('유형 합계')

for label, ids in (('흐름축', flow_ids), ('관리웹 트리', tree_ids), ('POP 모드', pop_ids), ('모바일 타일', tile_ids)):
    dup = [k for k, v in Counter(ids).items() if v > 1]
    if dup: die('%s 중복 배치: %s' % (label, dup))
    bad = [s for s in ids if s not in BY]
    if bad: die('%s 미등록 ID(결번 잔존 의심): %s' % (label, bad))

if set(flow_ids) != set(BY): die('흐름축 차집합: %s' % sorted(set(BY) ^ set(flow_ids)))
ia_ids = set(tree_ids) | set(pop_ids) | set(tile_ids)
if ia_ids != set(BY): die('IA 3모델 차집합: %s' % sorted(set(BY) ^ ia_ids))
if len(tree_ids) != 68 or len(pop_ids) != 22 or len(tile_ids) != 19:
    die('IA 계수 트리%d POP%d 타일%d' % (len(tree_ids), len(pop_ids), len(tile_ids)))
if VACATED & set(BY): die('결번이 현행 화면에 존재: %s' % sorted(VACATED & set(BY)))
if len(VACATED) != 11: die('결번 %d건 (11 아님)' % len(VACATED))

# 이월·차단 참조 ID 유효성 (결번 참조 금지)
for ids, *_ in CARRY:
    for s in ids:
        if s not in BY: die('이월 요건이 미등록 ID 참조: ' + s)
for *_, ids, _, _ in [(b[0], b[1], b[2], b[3], b[4], b[5]) for b in BLOCKERS]:
    pass
for b in BLOCKERS:
    for s in b[3]:
        if s not in BY: die('차단 원인이 미등록 ID 참조: ' + s)

# ════════════════════════════════════════════════════════════════════════════
# 4. 렌더 헬퍼
# ════════════════════════════════════════════════════════════════════════════

def esc(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

def md_inline(t):
    """데이터 유래 문자열 — 이스케이프 후 마크다운 변환."""
    t = esc(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    return t

def rich(t):
    """생성기가 직접 쓴 문장 — 의도한 HTML(<b>·<s>)을 살린다. 이스케이프하지 않는다."""
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    return t

CONF_CLS = {'확정': '', '추정': ' est', '미정': ' und'}
CONF_TAG = {'확정': '', '추정': '<i>추정</i>', '미정': '<i>?</i>'}

def chip(sid, tag=True):
    """미등록 ID 는 예외 — 선례의 조용한 실패(빈 문자열 반환)를 없앤다."""
    if sid not in BY:
        die('chip(): 미등록 ID ' + sid)
    r = BY[sid]
    new = ' new' if sid in {n[0] for n in NEW3} else ''
    return '<span class="chip %s%s%s" data-id="%s" title="%s"><b>%s</b>%s%s</span>' % (
        r['prog'], CONF_CLS[r['conf']], new, sid, esc(r['name'] + ' · ' + r['type'] + ' · ' + r['actor']),
        sid, esc(r['name']), CONF_TAG[r['conf']] if tag else '')

def dead_chip(sid, name, prog, kind, show_mark=True):
    mark = {'del': '✕', 'merge': '⊕', 'move': '↗', 'demote': '↓'}[kind]
    return '<span class="chip %s dead"><b>%s</b>%s%s</span>' % (
        prog, sid, esc(name), '<i>%s</i>' % mark if show_mark else '')

def lane_row(prog, ids, label):
    inner = ''.join(chip(x) for x in ids) or '<span class="none">—</span>'
    return '<div class="fl %s"><i>%s</i><div>%s</div></div>' % (prog, label, inner)

def flow_block(rows_):
    out = []
    for key, label, dom, wf, lanes in rows_:
        n = sum(len(v) for v in lanes.values())
        out.append(
            '<div class="frow"><div class="fst"><b>%s</b><span>%s · %d건</span><span class="wf">%s</span></div>'
            '<div class="flanes">%s%s%s</div></div>' % (
                esc(label), dom, n, esc(wf),
                lane_row('web', lanes['web'], 'WEB'), lane_row('pop', lanes['pop'], 'POP'),
                lane_row('mob', lanes['mob'], 'MOBILE')))
    return ''.join(out)

# ════════════════════════════════════════════════════════════════════════════
# 5. 도식 조립
# ════════════════════════════════════════════════════════════════════════════

# ── F1 업무 흐름 × 3레인
f1 = flow_block(STAGES)
f1_bands = ''.join(
    '<div class="frow band"><div class="fst"><b>%s</b><span>%d건</span><span class="wf">%s</span></div>'
    '<div class="flanes">%s%s%s</div></div>' % (
        esc(k), sum(len(v) for v in lanes.values()), esc(wf),
        lane_row('web', lanes['web'], 'WEB'), lane_row('pop', lanes['pop'], 'POP'),
        lane_row('mob', lanes['mob'], 'MOBILE'))
    for k, desc, wf, lanes in BANDS)
f1_band_desc = ''.join('<li><b>%s</b> — %s</li>' % (esc(k), rich(desc)) for k, desc, _, _ in BANDS)
f1_moves = ''.join('<li>%s <b>%s</b> — %s</li>' % (chip(i, False), esc(mv), rich(why)) for i, mv, why in MOVES)

# ── F2 단말 전환 사다리 (단계 경계는 계산 — 레인 점유 변화)
def occupancy(lanes):
    return [p for p in ('web', 'pop', 'mob') if lanes[p]]

PNAME  = {'web': 'WEB', 'pop': 'POP', 'mob': 'MOBILE'}
PSHORT = {'web': '웹', 'pop': 'POP', 'mob': '모바일'}
ORDER  = ('web', 'pop', 'mob')

ladder, prev = [], None
for key, label, dom, wf, lanes in STAGES:
    occ = occupancy(lanes)
    if prev is None:
        delta = ''
    else:
        add  = [p for p in ORDER if p in occ and p not in prev]
        drop = [p for p in ORDER if p in prev and p not in occ]
        delta = ' '.join(['+' + PSHORT[p] for p in add] + ['−' + PSHORT[p] for p in drop])
    ladder.append({'label': label, 'occ': occ, 'delta': delta,
                   'n': sum(len(v) for v in lanes.values())})
    prev = occ

f2_cols = ''.join(
    '<div class="lcol%s"><div class="lstage">%s</div>%s<div class="lshift">%s</div></div>' % (
        ' on' if st['delta'] else '', esc(st['label']),
        ''.join('<div class="lcell %s%s">%s</div>' % (
            p, ' has' if p in st['occ'] else '', PNAME[p] if p in st['occ'] else '·')
            for p in ORDER),
        esc(st['delta']))
    for st in ladder)
f2_stacks = ''.join(
    '<div class="stk"><b>%s</b><span>%s</span><div>%s</div><p>%s</p></div>' % (
        esc(w), esc(what), ''.join(chip(i, False) + ('<em>⇄</em>' if n == 0 else '')
                                   for n, (i, _) in enumerate(scr)), rich(ev))
    for w, what, scr, ev in STACKS)
f2_notes = ''.join('<li><b>%s</b> — %s</li>' % (esc(t), rich(b)) for t, b in SHIFT_NOTES)

# ── F3 확정도 × 도메인 그리드 (커버리지 담당 1)
DOMS = [('01', '자재창고관리'), ('02', '생산실행'), ('03', '품질관리'), ('04', '제품출하'),
        ('05', '설비·툴 관리'), ('06', '기준정보·연계'), ('CO', '공통')]
CONFS = ['확정', '추정', '미정']
cell = defaultdict(list)
for r in ROWS:
    cell[(r['dom'], r['conf'])].append(r['id'])
f3_rows = ''
for dcode, dname in DOMS:
    tds = ''
    for cf in CONFS:
        ids = sorted(cell[(dcode, cf)])
        tds += '<td class="gc%s">%s</td>' % (
            CONF_CLS[cf], ''.join(chip(i, False) for i in ids) or '<span class="none">—</span>')
    tot = sum(len(cell[(dcode, cf)]) for cf in CONFS)
    f3_rows += '<tr><th>%s<span>%s</span><em>%d</em></th>%s</tr>' % (dcode, esc(dname), tot, tds)
f3_foot = ''.join('<td class="tot">%d</td>' % sum(len(cell[(d, cf)]) for d, _ in DOMS) for cf in CONFS)

bars = ''
for p, pname, total in (('web', '관리웹', 68), ('pop', 'POP', 22), ('mob', '모바일', 19)):
    segs, pct = '', {}
    for cf in CONFS:
        n = sum(1 for r in ROWS if r['prog'] == p and r['conf'] == cf)
        pct[cf] = n
        if n:
            segs += '<div class="seg%s" style="flex:%d"><span>%s %d</span></div>' % (CONF_CLS[cf], n, cf, n)
    rate = round(100.0 * pct['확정'] / total)
    ids_soft = [r['id'] for r in ROWS if r['prog'] == p and r['conf'] != '확정']
    bars += ('<div class="barrow"><div class="blab"><b>%s</b><span>%d건 · 확정 %d%%</span></div>'
             '<div class="bar %s">%s</div><div class="bsoft">%s</div></div>') % (
        pname, total, rate, p, segs,
        ''.join(chip(i, False) for i in ids_soft) if len(ids_soft) <= 8 else '추정·미정 %d건' % len(ids_soft))

# ── F4 IA 3모델 병렬 (커버리지 담당 2)
tree_html = ''.join(
    '<div class="t1"><h4>%s <em>%d</em></h4>%s</div>' % (
        esc(top), sum(len(ids) for _, ids in gs),
        ''.join('<div class="t2"><span class="t2n">%s</span><div class="t3">%s</div></div>' % (
            esc(g), ''.join(chip(x) for x in ids)) for g, ids in gs))
    for top, gs in TREE)
pop_html = ''.join(
    '<div class="pstep"><span class="pn">%s</span><p>%s</p><div>%s</div></div>' % (
        esc(n), esc(note), ''.join(chip(x) for x in ids))
    for n, ids, note in POP_MODES)
tile_html = ''.join(
    '<div class="tile"><span class="ic">%s</span><span class="tn">%s</span><div>%s</div></div>' % (
        i, esc(n), ''.join(chip(x) for x in ids)) for i, n, ids in TILES)
mob_entry_html = ''.join(chip(x) for x in MOB_ENTRY)
shell_html = ''.join(
    '<div class="shellcard %s"><b>%s</b><ul>%s</ul></div>' % (
        p, esc(lab), ''.join('<li>%s</li>' % rich(x) for x in items))
    for p, lab, items in SHELL)

IA_COMPARE = [
 ('탐색 단위', '메뉴 항목 (라우터)', 'W/O 태스크 (스텝퍼)', '스캔 타일 (홈)'),
 ('진입 · 인증', '계정 로그인 · 온라인 전제', '사번 경량 인증 · 로그인 생략', '계정 + 기기 등록 · 스캐너 페어링'),
 ('깊이', '2계층 (7 대분류 × 소그룹 20)', '모드 6 × 스텝 (평탄)', '타일 9 (1계층)'),
 ('상시 요소', '헤더 — 한/베 토글 · 알림 배지', '상태바 — 오프라인·미동기 N건', '언어 선택 (진입)'),
]
ia_cmp = ''.join('<tr><th>%s</th><td class="web">%s</td><td class="pop">%s</td><td class="mob">%s</td></tr>'
                 % (esc(a), esc(b), esc(c_), esc(d_)) for a, b, c_, d_ in IA_COMPARE)

# ── F5 외부 의존
f5_block = ''
MAXN = max(len(b[3]) for b in BLOCKERS) or 1
for name, what, who, ids, detail, eff in BLOCKERS:
    w = int(100.0 * len(ids) / MAXN) if ids else 0
    f5_block += (
        '<div class="cause"><div class="cn"><b>%s</b><span>%s</span><em class="who">%s</em></div>'
        '<div class="cw"><i style="width:%d%%"></i><u>%s</u><s class="eff">%s</s></div>'
        '<div class="cf">%s<p>%s</p></div></div>') % (
        esc(name), esc(what), esc(who), w,
        '%d건' % len(ids) if ids else '화면 미특정', eff,
        ''.join(chip(i, False) for i in ids) or '<span class="none">화면 미특정 — 원인만 확정</span>',
        rich(detail))

f5_carry = ''.join(
    '<div class="carry"><div>%s</div><p>%s <span>· %s</span></p></div>' % (
        ''.join(chip(i, False) for i in ids) or '<span class="none">전역 원칙 (화면 부착 없음)</span>',
        rich(req), rich(why)) for ids, req, why in CARRY)

# ── F6 판정 실례
f6 = ''
for rule, desc, pairs in PAIRS:
    cells = ''
    GMAP = {g[0]: g for g in GONE}
    for (a, b), sym, note in pairs:
        def side(s):
            if s in BY:
                return chip(s, False)
            if s in GMAP:
                g = GMAP[s]
                return dead_chip(g[0], g[1], g[2], g[3], show_mark=False)
            die('PAIRS 미등록 ID: ' + s)
        ca, cb = side(a), side(b)
        cells += '<div class="pair">%s<em>%s</em>%s<p>%s</p></div>' % (ca, sym, cb, rich(note))
    f6 += '<div class="prow"><div class="pk"><b>%s</b><span>%s</span></div><div class="pv">%s</div></div>' % (
        esc(rule), rich(desc), cells)

# ── F7 프로그램 × 유형
TYPES = ['입력', '스캔', '판정·승인', '조회·상세', '목록', '설정·마스터', '출력·인쇄', '대시보드']
tcount = defaultdict(list)
for r in ROWS:
    tcount[(r['prog'], r['type'])].append(r['id'])
if sum(len(v) for v in tcount.values()) != 109: die('유형 교차 합계')
unknown = {r['type'] for r in ROWS} - set(TYPES)
if unknown: die('미등록 유형: %s' % unknown)

f7_bars = ''
for p, pname, total in (('web', '관리웹', 68), ('pop', 'POP', 22), ('mob', '모바일', 19)):
    segs = ''
    for i, t in enumerate(TYPES):
        n = len(tcount[(p, t)])
        if n:
            segs += '<div class="tseg %s s%d" style="flex:%d"><span>%s %d</span></div>' % (p, i, n, esc(t), n)
    f7_bars += '<div class="barrow"><div class="blab"><b>%s</b><span>%d건</span></div><div class="bar">%s</div></div>' % (
        pname, total, segs)
f7_rows = ''
for t in TYPES:
    tds = ''
    for p in ('web', 'pop', 'mob'):
        ids = sorted(tcount[(p, t)])
        tds += '<td>%s</td>' % (''.join(chip(i, False) for i in ids) or '<span class="none">—</span>')
    n = sum(len(tcount[(p, t)]) for p in ('web', 'pop', 'mob'))
    f7_rows += '<tr><th>%s<em>%d</em></th>%s</tr>' % (esc(t), n, tds)

# ── F8 인증·권한
f8_cards = ''.join(
    '<div class="acard %s"><span class="ap">%s</span>%s<b>%s</b><ul>%s</ul></div>' % (
        p, esc(pname), chip(sid, False), esc(kind), ''.join('<li>%s</li>' % rich(x) for x in items))
    for p, pname, sid, kind, items in AUTH)
f8_gates = ''.join('<div class="gate">%s<span>🔒 %s</span></div>' % (chip(i, False), esc(w)) for i, w in GATES)

# ── F9 전건 목록
J_ROWS = [[r['id'], r['name'], r['type'], r['actor'], r['conf'], r['prog'], r['dom'],
           r['why'], next((b[0] for b in BLOCKERS if r['id'] in b[3]), ''),
           1 if any(r['id'] in ids for ids, _, _ in CARRY) else 0] for r in ROWS]
J_GONE = [[g[0], g[1], g[2], g[3], ' · '.join('%s(%s)' % (t[0], t[1]) for t in g[4]), g[5]] for g in GONE]

VERSION_FLOW = [('원 열거', 120, ''), ('중복 8 병합', 112, 'v1.0'), ('적대 검증', 112, 'v1.1'),
                ('2계층 매핑 4단계', 113, 'v1.2'), ('비도식 근거 규칙', 109, 'v1.3')]
vflow = ''.join('<div class="vstep%s"><b>%d</b><span>%s</span><em>%s</em></div>' % (
    ' cur' if i == len(VERSION_FLOW) - 1 else '', n, esc(lab), esc(v)) for i, (lab, n, v) in enumerate(VERSION_FLOW))

# ════════════════════════════════════════════════════════════════════════════
# 6. HTML
# ════════════════════════════════════════════════════════════════════════════

CSS = '''
*,*::before,*::after{box-sizing:border-box}
:root{
 --bg:#f6f7f9; --card:#fff; --ink:#16181d; --dim:#5c6270; --line:#e3e6ec; --soft:#f0f2f5;
 --web:#2F6FED; --pop:#F2994A; --mob:#27AE60;
 --webbg:#eaf1fe; --popbg:#fef2e6; --mobbg:#e8f7ee;
 --webink:#1b4fbf; --popink:#a5620f; --mobink:#166d3b;
}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--ink:#e8eaf0;--dim:#98a0b0;--line:#272c36;
 --soft:#1d212a;--webbg:#16233d;--popbg:#33240f;--mobbg:#10291b;--webink:#8fb3f8;--popink:#f0ad63;--mobink:#5ecb8c}}
:root[data-theme=dark]{--bg:#0f1115;--card:#171a21;--ink:#e8eaf0;--dim:#98a0b0;--line:#272c36;--soft:#1d212a;
 --webbg:#16233d;--popbg:#33240f;--mobbg:#10291b;--webink:#8fb3f8;--popink:#f0ad63;--mobink:#5ecb8c}
:root[data-theme=light]{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--dim:#5c6270;--line:#e3e6ec;--soft:#f0f2f5;
 --webbg:#eaf1fe;--popbg:#fef2e6;--mobbg:#e8f7ee;--webink:#1b4fbf;--popink:#a5620f;--mobink:#166d3b}
html,body{overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased;
 font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
.wrap{max-width:1320px;margin:0 auto;padding:30px 18px 90px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--dim);margin:0 0 22px;font-size:13px}
h2{font-size:17px;margin:46px 0 4px;letter-spacing:-.01em}
h2 small{font-weight:400;font-size:12px;color:var(--dim);margin-left:8px}
h3{font-size:14px;margin:22px 0 8px}
.lead{color:var(--dim);margin:0 0 14px;font-size:13px;max-width:88ch}
.q{margin:0 0 14px;font-size:12.5px;color:var(--dim);border-left:3px solid var(--line);padding:2px 0 2px 10px}
.q b{color:var(--ink);font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.scroll{overflow-x:auto}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(146px,1fr));gap:10px;margin:0 0 8px}
.kpi div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 15px}
.kpi b{display:block;font-size:27px;letter-spacing:-.03em;line-height:1.15}
.kpi span{font-size:11px;color:var(--dim)}
/* 칩 — 색=프로그램 / 테두리=신뢰도 / 기호=변동 */
.chip{display:inline-flex;align-items:center;gap:5px;border-radius:7px;padding:3px 8px;margin:3px 4px 3px 0;
 font-size:12px;border:1px solid transparent;white-space:nowrap;cursor:default;max-width:100%}
.chip b{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;font-weight:600;opacity:.85}
.chip i{font-style:normal;font-size:9.5px;opacity:.75;letter-spacing:.02em}
.chip.web{background:var(--webbg);color:var(--webink);border-color:color-mix(in srgb,var(--web) 28%,transparent)}
.chip.pop{background:var(--popbg);color:var(--popink);border-color:color-mix(in srgb,var(--pop) 38%,transparent)}
.chip.mob{background:var(--mobbg);color:var(--mobink);border-color:color-mix(in srgb,var(--mob) 32%,transparent)}
.chip.est{border-style:dashed}
.chip.und{border-style:double;border-width:2px}
.chip.new::after{content:"✦";font-size:10px;opacity:.85}
.chip.dead{opacity:.6;background:var(--soft);border-color:var(--line);text-decoration:line-through}
.chip.dead i{text-decoration:none;opacity:1;font-size:11px}
.none{color:var(--dim);opacity:.55;font-size:12px}
/* 범례 */
.legend{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin:0 0 10px;font-size:12px;color:var(--dim)}
.legend b{color:var(--ink)}
.rule{background:var(--soft);border:1px dashed var(--line);border-radius:10px;padding:11px 14px;font-size:12.5px;
 color:var(--dim);margin:0 0 16px}
.rule b{color:var(--ink)}
/* F1 흐름 */
.flow{min-width:920px}
.frow{display:grid;grid-template-columns:150px 1fr;border-bottom:1px solid var(--line)}
.frow:last-child{border-bottom:0}
.frow.band{background:color-mix(in srgb,var(--soft) 60%,transparent)}
.fst{padding:11px 12px 11px 0;border-right:2px solid var(--line);position:relative}
.fst b{display:block;font-size:13px;letter-spacing:-.01em}
.fst span{display:block;font-size:11px;color:var(--dim)}
.fst .wf{font-size:10px;opacity:.75;margin-top:2px;font-family:ui-monospace,Menlo,monospace}
.fst::after{content:"";position:absolute;right:-5px;top:16px;width:8px;height:8px;border-radius:50%;background:var(--line)}
.flanes{display:grid}
.fl{display:grid;grid-template-columns:58px 1fr;align-items:center;gap:8px;padding:4px 0 4px 12px;
 border-bottom:1px dashed color-mix(in srgb,var(--line) 65%,transparent)}
.fl:last-child{border-bottom:0}
.fl>i{font-style:normal;font-size:9.5px;font-weight:700;letter-spacing:.05em;text-align:right;opacity:.7}
.fl.web>i{color:var(--web)}.fl.pop>i{color:var(--popink)}.fl.mob>i{color:var(--mobink)}
/* F2 사다리 */
.ladder{display:flex;gap:0;min-width:900px}
.lcol{flex:1;min-width:96px;padding:0 6px;border-right:1px dashed var(--line);text-align:center}
.lcol.on{background:color-mix(in srgb,var(--soft) 70%,transparent)}
.lcol:last-child{border-right:0}
.lstage{font-size:11px;color:var(--dim);height:34px;display:flex;align-items:center;justify-content:center;
 line-height:1.25;border-bottom:1px solid var(--line)}
.lcell{height:30px;margin:5px 0;border-radius:6px;font-size:9.5px;font-weight:700;letter-spacing:.04em;
 display:flex;align-items:center;justify-content:center;color:var(--dim);background:var(--soft);opacity:.45}
.lcell.has{opacity:1}
.lcell.web.has{background:var(--webbg);color:var(--webink)}
.lcell.pop.has{background:var(--popbg);color:var(--popink)}
.lcell.mob.has{background:var(--mobbg);color:var(--mobink)}
.lshift{font-size:10px;height:18px;color:var(--dim);font-weight:600}
.lshift{white-space:nowrap}
.lcol.on .lshift{color:var(--ink)}
.stk{border:1px solid var(--line);border-radius:10px;padding:11px 13px;margin-bottom:9px;background:var(--card)}
.stk b{font-size:12px;font-family:ui-monospace,Menlo,monospace}
.stk span{font-size:12px;color:var(--dim);margin-left:8px}
.stk em{font-style:normal;opacity:.6;margin:0 3px}
.stk p{margin:4px 0 0;font-size:11px;color:var(--dim)}
/* F3 그리드 */
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
thead th{background:var(--soft);font-size:12px;white-space:nowrap}
.grid{min-width:880px}
.grid th:first-child{width:130px;white-space:nowrap}
.grid th:first-child span{display:block;font-weight:400;font-size:11px;color:var(--dim)}
.grid th:first-child em{font-style:normal;font-size:11px;color:var(--dim)}
.gc.est{background:color-mix(in srgb,var(--soft) 55%,transparent)}
.gc.und{background:color-mix(in srgb,var(--soft) 85%,transparent)}
td.tot{font-weight:700;text-align:center;font-variant-numeric:tabular-nums}
.barrow{display:grid;grid-template-columns:120px 1fr;gap:10px;align-items:center;margin-bottom:9px}
.barrow .bsoft{grid-column:2;margin-top:-4px}
.blab b{display:block;font-size:13px}.blab span{font-size:11px;color:var(--dim)}
.bar{display:flex;height:30px;border-radius:8px;overflow:hidden;border:1px solid var(--line)}
.bar>div{display:flex;align-items:center;justify-content:center;min-width:0;font-size:10.5px;font-weight:600}
.bar>div span{padding:0 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar.web>.seg{background:color-mix(in srgb,var(--web) 30%,transparent);color:var(--webink)}
.bar.pop>.seg{background:color-mix(in srgb,var(--pop) 38%,transparent);color:var(--popink)}
.bar.mob>.seg{background:color-mix(in srgb,var(--mob) 32%,transparent);color:var(--mobink)}
.bar>.seg.est{background:repeating-linear-gradient(45deg,color-mix(in srgb,var(--ink) 14%,transparent) 0 4px,transparent 4px 8px)}
.bar>.seg.und{background:transparent;outline:1.5px dashed var(--dim);outline-offset:-3px}
/* F4 IA */
.ia{display:grid;grid-template-columns:1.3fr .95fr .9fr;gap:14px;align-items:start}
@media (max-width:1020px){.ia{grid-template-columns:1fr}}
.iacol{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.iacol>h3{margin-top:0}
.t1{margin-bottom:11px;padding-bottom:9px;border-bottom:1px solid var(--line)}
.t1:last-child{border-bottom:0;margin-bottom:0;padding-bottom:0}
.t1 h4{margin:0 0 5px;font-size:12.5px}
.t1 h4 em{font-style:normal;font-size:10.5px;color:var(--dim);margin-left:5px}
.t2{display:grid;grid-template-columns:96px 1fr;gap:6px;align-items:start;padding:2px 0}
.t2n{font-size:11px;color:var(--dim);padding-top:6px}
.pstep{border-left:2px solid var(--line);padding:0 0 10px 12px;margin-left:4px;position:relative}
.pstep::before{content:"";position:absolute;left:-6px;top:4px;width:9px;height:9px;border-radius:50%;
 background:var(--card);border:2px solid color-mix(in srgb,var(--pop) 55%,transparent)}
.pn{font-size:12px;font-weight:600}
.pstep p{margin:1px 0 3px;font-size:10.5px;color:var(--dim)}
.tile{border:1px solid var(--line);border-radius:10px;padding:9px 11px;margin-bottom:8px}
.tile .ic{font-size:15px;margin-right:6px}
.tile .tn{font-size:12px;font-weight:600}
.entry{border:1px dashed color-mix(in srgb,var(--mob) 45%,transparent);border-radius:10px;padding:9px 11px;
 margin-bottom:10px;background:color-mix(in srgb,var(--mobbg) 55%,transparent)}
.entry b{font-size:11.5px;display:block;margin-bottom:3px}
.cmp th{width:96px;font-size:11.5px}
.cmp td{font-size:11.5px}
.cmp td.web{color:var(--webink)}.cmp td.pop{color:var(--popink)}.cmp td.mob{color:var(--mobink)}
.shellrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;margin-top:12px}
.shellcard{border:1px dashed var(--line);border-radius:10px;padding:11px 13px;background:var(--soft)}
.shellcard b{font-size:12px}
.shellcard.web b{color:var(--webink)}.shellcard.pop b{color:var(--popink)}.shellcard.mob b{color:var(--mobink)}
.shellcard ul{margin:5px 0 0;padding-left:16px;font-size:11.5px;color:var(--dim)}
/* F5 의존 */
.cause{display:grid;grid-template-columns:230px 96px 1fr;gap:12px;padding:11px 0;border-bottom:1px solid var(--line)}
.cause:last-child{border-bottom:0}
@media (max-width:880px){.cause{grid-template-columns:1fr}}
.cn b{display:block;font-size:12.5px}
.cn span{font-size:11px;color:var(--dim);display:block}
.who{font-style:normal;font-size:10px;color:var(--dim);border:1px solid var(--line);border-radius:5px;
 padding:1px 5px;display:inline-block;margin-top:3px}
.cw{padding-top:3px}
.cw i{display:block;height:6px;border-radius:3px;background:currentColor;opacity:.28;margin-bottom:3px;min-width:2px}
.cw u{text-decoration:none;font-size:11px;color:var(--dim)}
.cw .eff{text-decoration:none;font-size:11px;font-weight:700;margin-left:6px;opacity:.8}
.cf p{margin:3px 0 0;font-size:11px;color:var(--dim)}
.carry{display:grid;grid-template-columns:minmax(180px,300px) 1fr;gap:12px;padding:9px 0;border-bottom:1px dashed var(--line)}
.carry:last-child{border-bottom:0}
.carry p{margin:0;font-size:12px}
.carry p span{font-size:10.5px;color:var(--dim);white-space:nowrap}
@media (max-width:760px){.carry{grid-template-columns:1fr}}
/* F6 판정 */
.prow{display:grid;grid-template-columns:190px 1fr;gap:12px;padding:11px 0;border-bottom:1px solid var(--line)}
.prow:last-child{border-bottom:0}
@media (max-width:820px){.prow{grid-template-columns:1fr}}
.pk b{display:block;font-size:12.5px}
.pk span{font-size:11px;color:var(--dim)}
.pair{display:inline-block;border:1px solid var(--line);border-radius:9px;padding:5px 8px;margin:0 7px 7px 0;
 background:var(--card);vertical-align:top;max-width:100%}
.pair em{font-style:normal;font-size:13px;opacity:.7;margin:0 3px}
.pair p{margin:2px 0 0;font-size:10.5px;color:var(--dim);max-width:44ch}
/* F7 유형 */
.tseg{color:#fff}
.tseg.web{background:color-mix(in srgb,var(--web) var(--a,26%),transparent);color:var(--webink)}
.tseg.pop{background:color-mix(in srgb,var(--pop) var(--a,34%),transparent);color:var(--popink)}
.tseg.mob{background:color-mix(in srgb,var(--mob) var(--a,30%),transparent);color:var(--mobink)}
.tseg.s0{--a:46%}.tseg.s1{--a:40%}.tseg.s2{--a:34%}.tseg.s3{--a:28%}
.tseg.s4{--a:23%}.tseg.s5{--a:18%}.tseg.s6{--a:13%}.tseg.s7{--a:9%}
.tmx th:first-child{width:112px;white-space:nowrap}
.tmx th em{font-style:normal;font-size:11px;color:var(--dim);margin-left:5px}
/* F8 인증 */
.auth{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.acard{border:1px solid var(--line);border-radius:12px;padding:13px;background:var(--card)}
.acard .ap{font-size:10px;font-weight:700;letter-spacing:.05em;opacity:.75}
.acard.web .ap{color:var(--web)}.acard.pop .ap{color:var(--popink)}.acard.mob .ap{color:var(--mobink)}
.acard b{display:block;font-size:13px;margin:5px 0 4px}
.acard ul{margin:0;padding-left:16px;font-size:11.5px;color:var(--dim)}
.gates{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.gate{border:1px solid var(--line);border-radius:9px;padding:6px 9px;background:var(--soft)}
.gate span{font-size:10.5px;color:var(--dim);display:block}
/* F9 목록 */
.vsteps{display:flex;flex-wrap:wrap;gap:0;align-items:stretch;margin-bottom:14px}
.vstep{padding:9px 15px 9px 12px;border:1px solid var(--line);border-right:0;background:var(--card);min-width:120px}
.vstep:last-child{border-right:1px solid var(--line)}
.vstep.cur{background:var(--soft)}
.vstep b{display:block;font-size:19px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.vstep span{font-size:10.5px;color:var(--dim);display:block}
.vstep em{font-style:normal;font-size:9.5px;opacity:.6;font-family:ui-monospace,Menlo,monospace}
.ctl{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-bottom:10px}
.ctl input{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:7px 10px;
 font-size:12.5px;min-width:190px;font-family:inherit}
.ctl button{border:1px solid var(--line);background:var(--card);color:var(--dim);border-radius:8px;padding:6px 10px;
 font-size:11.5px;cursor:pointer;font-family:inherit}
.ctl button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.ctl .cnt{font-size:12px;color:var(--dim);margin-left:auto;font-variant-numeric:tabular-nums}
#lst{min-width:1000px}
#lst td,#lst th{font-size:12px}
#lst tbody th{font-family:ui-monospace,Menlo,monospace;font-size:11px;white-space:nowrap}
#lst .cf{white-space:nowrap;font-size:11px}
#lst .cf.c2{border-bottom:1px dashed var(--dim);display:inline-block;line-height:1.3}
#lst .cf.c3{border-bottom:2px double var(--dim);display:inline-block;line-height:1.3;font-weight:600}
#lst .bl{font-size:10.5px;color:var(--dim);white-space:nowrap}
#lst .wy{font-size:10.5px;color:var(--dim)}
.foot{margin-top:56px;padding-top:16px;border-top:1px solid var(--line);font-size:11.5px;color:var(--dim)}
.foot b{color:var(--ink)}
.foot ul{padding-left:17px;margin:6px 0}
@media print{
 body{background:#fff}.wrap{max-width:none;padding:0}
 .scroll{overflow:visible}.flow,.ladder,.grid,#lst,.ia{min-width:0}
 h2{break-after:avoid}.frow,.prow,.cause,.carry,.acard,.stk{break-inside:avoid}
 .ctl{display:none}
 .bar>.seg.est{background:none;outline:1px dashed #666;outline-offset:-3px}
}
'''

JS = '''
var R=%s,G=%s,fp='',fd='',fc='',fb=0,q='',showG=0;
function chipH(id,nm,pg,cf){var c='chip '+pg+(cf==='추정'?' est':cf==='미정'?' und':'');
 return '<span class="'+c+'"><b>'+id+'</b>'+nm+'</span>';}
function draw(){var tb=document.getElementById('tb'),h='',n=0;
 for(var i=0;i<R.length;i++){var r=R[i];
  if(fp&&r[5]!==fp)continue; if(fd&&r[6]!==fd)continue; if(fc&&r[4]!==fc)continue;
  if(fb&&!r[8]&&!r[9])continue;
  if(q){var s=(r[0]+' '+r[1]+' '+r[2]+' '+r[3]+' '+r[7]).toLowerCase();if(s.indexOf(q)<0)continue;}
  n++;
  h+='<tr><th>'+r[0]+'</th><td>'+r[1]+'</td><td>'+r[2]+'</td><td>'+r[3]+'</td>'
   +'<td class="cf c'+(r[4]==='확정'?'1':r[4]==='추정'?'2':'3')+'">'+r[4]+'</td>'
   +'<td class="bl">'+(r[8]||'')+(r[9]?(r[8]?' · ':'')+'이월 요건':'')+'</td>'
   +'<td class="wy">'+r[7]+'</td></tr>';}
 if(showG){for(var j=0;j<G.length;j++){var g=G[j],mk={del:'✕ 삭제',merge:'⊕ 통합',move:'↗ 이관',demote:'↓ 격하'}[g[3]];
  h+='<tr class="gr"><th style="text-decoration:line-through;opacity:.6">'+g[0]+'</th>'
   +'<td style="opacity:.6"><s>'+g[1]+'</s></td><td class="cf">'+mk+'</td>'
   +'<td colspan="2" class="bl">→ '+g[4]+'</td><td colspan="2" class="wy">'+g[5]+' · <b>ID 재사용 금지</b></td></tr>';}}
 tb.innerHTML=h;document.getElementById('cnt').textContent=n+' / 109건'+(showG?' + 결번 '+G.length:'');}
function tg(el,k,v){var on=el.getAttribute('aria-pressed')==='true';
 var g=document.querySelectorAll('[data-k="'+k+'"]');for(var i=0;i<g.length;i++)g[i].setAttribute('aria-pressed','false');
 if(k==='p')fp=on?'':v; if(k==='d')fd=on?'':v; if(k==='c')fc=on?'':v;
 if(!on)el.setAttribute('aria-pressed','true');draw();}
document.addEventListener('DOMContentLoaded',function(){
 var s=document.getElementById('q');s.addEventListener('input',function(){q=s.value.trim().toLowerCase();draw();});
 var b=document.getElementById('bl');b.addEventListener('click',function(){fb=!fb;
  b.setAttribute('aria-pressed',fb?'true':'false');draw();});
 var gg=document.getElementById('gt');gg.addEventListener('click',function(){showG=!showG;
  gg.setAttribute('aria-pressed',showG?'true':'false');draw();});
 var ts=document.querySelectorAll('[data-k]');for(var i=0;i<ts.length;i++)(function(el){
  el.addEventListener('click',function(){tg(el,el.getAttribute('data-k'),el.getAttribute('data-v'));});})(ts[i]);
 draw();});
''' % (json.dumps(J_ROWS, ensure_ascii=False), json.dumps(J_GONE, ensure_ascii=False))

def sec(no, title, small, question, body, lead=''):
    return ('<h2>%s %s<small>%s</small></h2>%s<p class="q"><b>답하는 질문</b> — %s</p>%s'
            % (no, esc(title), esc(small), ('<p class="lead">%s</p>' % rich(lead)) if lead else '',
               rich(question), body))

HTML = '''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OMF-MES 통합 IA — 도식본</title>
<style>%(css)s</style></head><body><div class="wrap">

<h1>OMF-MES 통합 IA — 도식본</h1>
<p class="sub">화면 109건을 흐름·확정도·구조·의존으로 그린 9개 도식 · 작성일 2026-07-30 (v1.0) · CREFLE OMF 팀 · 내부 대외비<br>
정본 = <code>uiux/2026-07-25-화면목록-IA/screen-inventory-ia.md</code> v1.3 · 본 도식본은 <code>deliverables/04-통합-IA.md</code> 파생 ·
미결 스냅샷 기준일 <b>%(snap)s</b></p>

<div class="kpi">
 <div><b>109</b><span>화면 전건 · 관리웹 68 · POP 22 · 모바일 19</span></div>
 <div><b>82</b><span>확정 · 추정 25 · 미정 2</span></div>
 <div><b>9</b><span>업무 단계 (+ 흐름 밖 5밴드)</span></div>
 <div><b>3</b><span>IA 모델 — 메뉴트리 · 태스크모드 · 스캔타일</span></div>
 <div><b>16</b><span>상세 스펙 이월 요건</span></div>
 <div><b>11</b><span>결번 ID — 재사용 금지</span></div>
</div>

<div class="rule"><b>본 도식의 표시 규칙</b> — 색은 <b>프로그램</b>에만 쓴다(<span class="chip web"><b>W-</b>관리웹</span>
<span class="chip pop"><b>P-</b>POP</span> <span class="chip mob"><b>M-</b>모바일</span> — 배지 정책 색 §2-2).
신뢰도는 <b>형태</b>로만 — 실선 = 확정 · <span class="chip web est"><b>—</b>점선<i>추정</i></span> ·
<span class="chip web und"><b>—</b>이중선<i>?</i></span> 미정. 변동은 <b>기호</b>로만 — ✦ 신설 · <s>취소선</s> 결번 · ⊕ 통합 · ↗ 이관 · ↓ 격하.
<br>⚠ <b>파생 고백</b>: ① 9단계 업무 축은 <b>본 도식의 편집 판단</b>이다 — 정본에 「업무 단계」 열은 없고, 근거는 화면별 WF S-번호다.
② 단계 경계의 「전환」 표시는 레인 점유 변화를 <b>계산</b>한 것이다. ③ 미결·이월(⑤)은 §7·§8 언급 화면을 기계 대조한 것으로 정본의 등급 판정이 아니다.
착수 우선순위·역할 등급 같은 <b>발명은 하지 않았다</b>.
<br>⚠ <b>E-번호 이중 체계</b>: 본 도식의 E-1·E-3·E-4는 전부 <b>고객 회신 대기 코드</b>(회신 E-n)이며, WF 예외 카탈로그의 「예외 E-n」과 무관하다.</div>

%(f1)s
%(f2)s
%(f3)s
%(f4)s
%(f5)s
%(f6)s
%(f7)s
%(f8)s
%(f9)s

<div class="foot">
<b>근거</b> — 화면 109건·유형·행위자·신뢰도·근거 요지 = <code>deliverables/04-통합-IA.md</code> §3-2·§4-2·§5-2(생성기가 직접 파싱) ·
IA 3모델 = §3-1·§4-1·§5-1 · 배지·정책 = §2-2·§2-3 · 변동 = §6 · 미결 = §7 · 이월 요건 = §8 · 판정 규칙 = §9-1.
<ul>
<li><b>재생성</b> — <code>python3 build-04-ia-도식본.py</code>. md 를 고치면 화면·유형·행위자·신뢰도는 자동 반영되고,
흐름 배치·IA 트리·미결 상수는 생성기 상단에서 고친다. 빌드 assert(109·프로그램·도메인·신뢰도·유형·차집합·결번)가 어긋나면 생성이 중단된다.</li>
<li><b>선례</b> — <code>uiux/2026-07-25-화면목록-IA/화면목록-IA-도식본.html</code>(도식 6종)을 계승했다.
계승 중 발견한 선례의 결함 3건: ① 결번 <code>W-03-04</code>가 흐름 배치·메뉴 트리에 잔존(칩 함수가 미등록 ID를 빈 문자열로 삼켜 렌더에서 보이지 않았다)
② 모바일 타일이 진입 <code>M-CO-01</code>을 빠뜨려 18건 ③ 제목·본문 수치가 「108건」으로 정지. 본 도식본은 세 가지를 모두 고쳤다.</li>
<li><b>이 문서는 파생이다</b> — 화면의 추가·삭제·범위 변경은 정본에서만 결정한다. 도식에서 정본 오류를 발견하면 도식을 고치지 말고 이슈 경로(uiux↔docs 경계 규칙)를 따른다.</li>
</ul>
</div>
</div>
<script>%(js)s</script>
</body></html>
'''

f1_body = ('<div class="legend"><b>순방향 9단계</b> — 자재 입하부터 제품 출하까지 · 각 단계 안에 3개 레인</div>'
           '<div class="card scroll"><div class="flow">%s</div></div>'
           '<h3>흐름 밖 — 역흐름 · 횡단 · 상시 (5밴드 · 50건)</h3>'
           '<div class="card scroll"><div class="flow">%s</div></div>'
           '<ul class="lead">%s</ul>'
           '<h3>선례 배치에서 옮긴 3건 (근거가 프로세스 정본에 있는 것만)</h3><ul class="lead">%s</ul>'
           % (f1, f1_bands, f1_band_desc, f1_moves))

f2_body = ('<div class="card scroll"><div class="ladder">%s</div></div>'
           '<h3>같은 지점에 두 단말 — 배지 정본이 확정한 스택 3건</h3>%s'
           '<h3>읽히는 것</h3><ul class="lead">%s</ul>' % (f2_cols, f2_stacks, f2_notes))

f3_body = ('%s<div class="card scroll"><table class="grid"><thead><tr><th>도메인</th>'
           '<th>확정 <small>(도식+배지 명확)</small></th><th>추정 <small>(성격 판단)</small></th>'
           '<th>미정 <small>(회신 대기)</small></th></tr></thead><tbody>%s</tbody>'
           '<tfoot><tr><th class="tot">109</th>%s</tr></tfoot></table></div>'
           % (bars, f3_rows, f3_foot))

f4_body = ('<div class="card"><table class="cmp"><thead><tr><th></th><th class="web">관리웹</th>'
           '<th class="pop">POP</th><th class="mob">모바일</th></tr></thead><tbody>%s</tbody></table></div>'
           '<div class="ia" style="margin-top:14px">'
           '<div class="iacol"><h3>관리웹 — 메뉴 트리 <small>68건 · 7 대분류</small></h3>%s</div>'
           '<div class="iacol"><h3>POP — 태스크 모드 <small>22건 · 메뉴가 아니다</small></h3>%s</div>'
           '<div class="iacol"><h3>모바일 — 스캔 타일 <small>19건</small></h3>'
           '<div class="entry"><b>진입 — 로그인 · 기기 등록</b>%s</div>%s</div></div>'
           '<div class="shellrow">%s</div>'
           % (ia_cmp, tree_html, pop_html, mob_entry_html, tile_html, shell_html))

f5_body = ('<div class="card">%s</div>'
           '<h3>이미 정해진 것 — 상세 스펙에 반드시 반영할 요건 16건</h3><div class="card">%s</div>'
           % (f5_block, f5_carry))

out = io.open(DST, 'w', encoding='utf-8')
out.write(HTML % {
 'css': CSS, 'js': JS, 'snap': SNAPSHOT,
 'f1': sec('①', '업무 흐름 × 단말 3레인', '순방향 9단계 59건 + 흐름 밖 5밴드 50건 = 109',
           '이 공정이 스프린트에 잡혔다 — <b>어느 셸에 무슨 화면</b>을 만들어야 하고, 이 단계는 화면 몇 개짜리 일인가?',
           f1_body,
           '가로가 아니라 세로로 읽는다 — 한 단계 안에서 웹·POP·모바일 레인 중 어디가 비어 있는지가 그 단계의 성격이다.'),
 'f2': sec('②', '단말 전환 사다리', '전환 지점 · 스택 3건',
           '웹에서 POP으로, POP에서 PDA로 일이 넘어가는 지점이 어디고 <b>셸 간 인터페이스를 몇 개</b> 정의해야 하나?',
           f2_body,
           '레인 점유가 바뀌는 열이 전환 지점이다. 「스택」은 <b>같은 지점에 두 단말이 서는</b> 경우로, 배지 정본이 확정한 3건이다.'),
 'f3': sec('③', '확정도 × 도메인 — 109건이 전부 여기 있다', '커버리지 담당 1',
           '<b>내일 상세 스펙 착수해도 되는 화면</b>이 어느 도메인에 몇 개고, 흔들리는 건 어디에 몰려 있나?',
           f3_body,
           '확정 82는 v1.2→v1.3 정리에서 <b>한 건도 건드리지 않았다</b> — 줄어든 4건은 전부 추정·미정 쪽이었다.'),
 'f4': sec('④', 'IA 3모델 병렬 — 셸을 세 벌 만든다', '커버리지 담당 2 · 68 + 22 + 19',
           '내가 짜야 하는 셸은 <b>라우터·스텝퍼·타일</b> 중 뭔가? 메뉴 트리의 어느 묶음에 어느 화면이 들어가나?',
           f4_body,
           'React 코드는 1벌이지만 <b>탐색 모델은 세 벌</b>이다 — 관리웹은 메뉴 트리, POP은 W/O 태스크 모드(메뉴 아님), 모바일은 스캔 퍼스트 타일.'),
 'f5': sec('⑤', '화면 위의 외부 의존', '차단 원인 10 → 영향 화면 · 이월 요건 16',
           '고객 회신 한 건이 오면 <b>화면 몇 개가 풀리나</b>, 지금 손대면 헛일이 되는 화면은 어느 것인가?',
           f5_body,
           '왼쪽이 원인, 오른쪽이 영향 화면이다. 영향 기호 — <b>=</b> 화면 수 무영향 · <b>?</b> 존재·범위 유동 · <b>+</b> 신설 가능.'),
 'f6': sec('⑥', '분할 · 병합 판정 실례', '규칙 6 × 실례 11쌍',
           '왜 이건 두 화면이고 저건 한 화면인가? 구현하면서 <b>합치거나 쪼개면 무엇을 깨는가?</b>',
           f6,
           '기호 — <b>⇄</b> 분리 확정 · <b>⊕</b> 흡수·통합 확정 · <b>?</b> 검토 중. 취소선 칩은 결번(ID 재사용 금지)이다.'),
 'f7': sec('⑦', '프로그램 × 화면 유형 8종', '만들 컴포넌트의 성격',
           '내 프로그램에서 반복 생산할 UI는 뭔가 — 마스터 CRUD 폼인가, 스캔 입력기인가? <b>공용 컴포넌트를 어디에 투자</b>하면 이득이 큰가?',
           '%s<div class="card scroll"><table class="tmx"><thead><tr><th>유형</th><th class="web">관리웹</th>'
           '<th class="pop">POP</th><th class="mob">모바일</th></tr></thead><tbody>%s</tbody></table></div>'
           % (f7_bars, f7_rows),
           '같은 hue의 명도로 유형을 갈랐다 — 색 채널은 여전히 프로그램 하나만 뜻한다.'),
 'f8': sec('⑧', '인증 · 권한 3계층', '인증 4 + 권한 게이트 4',
           '인증을 세 벌 만들어야 하나? POP의 사번 인증은 로그인이 아닌데 <b>실적 귀속</b>은 어떻게 되나?',
           '<div class="auth">%s</div>'
           '<h3>권한 정본 · 게이트 화면</h3><div class="card">%s<div class="gates">%s</div></div>'
           % (f8_cards, chip('W-CO-02', False) + '<span class="none"> — role·권한 매트릭스의 정본. 아래 화면들이 이걸 참조한다</span>', f8_gates),
           'POP은 <b>로그인이 아니다</b> — 사번만 입력해 실적을 귀속시킨다(REQ-PR-0023). 단말 인증은 토큰 + 사번 3층 분리(POP인증 §6-①②③).'),
 'f9': sec('⑨', '전건 목록 — 109건 필터 · 결번 11건', '변동 궤적 120 → 109',
           '지금 잡은 티켓이 W-02-08인데 <b>단말·유형·신뢰도·차단 요인·근거</b>가 뭔가? 옛 문서의 W-02-09는 어디로 갔나?',
           '<div class="vsteps">%s</div>'
           '<div class="ctl"><input id="q" placeholder="ID · 화면명 · 행위자 · 근거 검색">'
           '<button data-k="p" data-v="web" aria-pressed="false">관리웹</button>'
           '<button data-k="p" data-v="pop" aria-pressed="false">POP</button>'
           '<button data-k="p" data-v="mob" aria-pressed="false">모바일</button>'
           '<button data-k="c" data-v="확정" aria-pressed="false">확정</button>'
           '<button data-k="c" data-v="추정" aria-pressed="false">추정</button>'
           '<button data-k="c" data-v="미정" aria-pressed="false">미정</button>'
           '<button id="bl" aria-pressed="false">차단·이월만</button>'
           '<button id="gt" aria-pressed="false">결번 11건 보기</button>'
           '<span class="cnt" id="cnt"></span></div>'
           '<div class="card scroll"><table id="lst"><thead><tr><th>ID</th><th>화면명</th><th>유형</th>'
           '<th>행위자</th><th>신뢰도</th><th>차단 · 이월</th><th>근거 요지</th></tr></thead>'
           '<tbody id="tb"></tbody></table></div>' % vflow,
           '결번은 토글로만 보인다 — 본 표에는 나오지 않는다. <b>ID 재사용 금지</b>(옛 문서·코드에서 만나면 흡수처를 따라간다).'),
})
out.close()
print('생성: %s (%.1f KB)' % (DST, os.path.getsize(DST) / 1024.0))
print('검산 통과 — 화면 109 · 흐름축 %d · IA 3모델 %d · 결번 %d' % (len(flow_ids), len(ia_ids), len(VACATED)))

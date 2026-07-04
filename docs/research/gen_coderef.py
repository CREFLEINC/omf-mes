# -*- coding: utf-8 -*-
import re, html, os

BASE="/Users/rangkim/projects/crefle/ohmyfactory/apps/omf/docs/research"
QFILE=os.path.join(BASE,"2026-07-03-현장검증-질문지-v2-요구사항통합.md")
OUT=os.path.join(BASE,"2026-07-03-현장점검-코드참조-미결코드·클러스터.html")

SECT={"A":"A · LOT·추적 (최우선 — 모델 골격)",
      "B":"B · 엔티티 키·정규화",
      "C":"C · 소유 경계 (엔티티 단일화)",
      "D":"D · 범위·보완 (권한·연계 등)",
      "E":"E · 요구사항 명세서 발 후속 확인 (2026-07-01 · 고객 액션 + 신규 미결)"}

def clean(q):
    status=""
    m0=re.match(r"^\*?\*?✓\[([^\]]*)\]",q)
    if m0:
        status="부분" if "부분" in m0.group(1) else "확정"
    elif re.match(r"^\*\*✓",q) or q.startswith("✓"):
        status="확정"
    # 머리 마커 제거
    q=re.sub(r"^\*\*✓\[[^\]]*\]\*\*\s*","",q)
    q=re.sub(r"^✓\[[^\]]*\]\s*","",q)
    q=re.sub(r"^\*\*\[[^\]]*\]\*\*\s*","",q)
    q=re.sub(r"^\[[^\]]*\]\s*","",q)
    # 강조·취소선 제거
    q=re.sub(r"\*\*(.+?)\*\*",r"\1",q)
    q=re.sub(r"\*(.+?)\*",r"\1",q)
    q=re.sub(r"~~(.+?)~~",r"\1",q)
    q=q.strip()
    # 첫 물음표까지(질문형) 또는 길이 제한
    m=re.search(r"^(.+?\?)",q)
    if m and len(m.group(1))<=160:
        q=m.group(1)
    elif len(q)>150:
        q=q[:150].rstrip()+"…"
    return status,q

rows={"A":[],"B":[],"C":[],"D":[],"E":[]}
for ln in open(QFILE,encoding="utf-8").read().splitlines():
    if not ln.startswith("|"): continue
    cells=[c.strip() for c in ln.strip().strip("|").split("|")]
    if len(cells)<2: continue
    code=cells[0]
    m=re.match(r"^([ABCDE])(\d+)$",code)
    if not m: continue
    rel=cells[-1] if len(cells)>=5 else ""
    st,q=clean(cells[1])
    rows[m.group(1)].append((code,int(m.group(2)),st,q,rel))
for k in rows: rows[k].sort(key=lambda r:r[1])

# 데이터모델 v2(2026-07-03-개념데이터모델-v2-요구사항통합.md) 기준 6대 클러스터 요약
CLUSTERS=[
 ("C1","기준정보 (Master)","품목(+개발품 구분)·BOM·공정/Routing(정본=MES ✓)·검사항목·불량코드(처분구분·퍼징/시작불량)·설비·툴/금형/지그(정본=MES+QR ✓)·작업자·창고Location(생산창고·불량창고 포함, 사용자 관리)·공통코드(다국어)·사용자/권한(✓신설)·공장 레이아웃·ERP-MES I/F","마스터 데이터. ERP 연계는 품목·BOM·공통코드·조직·작업자·P/O로 한정(공정·툴 제외 — 2026-07-01 확정), 연계분만 수정 불가 · MES 정본은 수정 가능+변경 이력."),
 ("C2","생산실행 (Production)","P/O(ERP 수신·변경 전파)·W/O(유형: 양산/긴급/개발품 · 상태 +중단/재시작/취소 · 마감 3분류)·작업홀드이력·자원배정(4M 계획)·4M투입(실적)·작업실적(사번 귀속)·전달사항","생산 지시의 전개·실행. P/O→W/O→작업실적→생산LOT. Routing 부재 시 BOM 기반 4M 계획 fallback(✓) · 러닝체인지 계획 분할."),
 ("C3","LOT코어 (LOT/추적)","자재LOT(사전발행→IQC 합격 시 생성 ✓)·자재LOT분할(QR·양방향 스캔)·생산LOT·제품LOT·인식표·포장단위","추적(genealogy)의 골격. 자재LOT 생성=IQC 합격(✓ 2026-07-01), 번호 사전발행은 별도 상태. 생산LOT=MES 발행 정본."),
 ("C4","품질 (Quality)","검사실적(IQC/PQC/OQC)·검사결과·품질기준값·검사정책(PQC 생략 옵션)·판정유형(합/불+보류·한도승인·특채·폐기)·Lot Status(Hold/Release)·의심자재 등록·수리(Repair) 추적·SPC측정값·계측기·비가동","검사·합부 판정·품질통제. 판정 유형 확장(목록 고객 회신 대기) · 수리 왕복 추적(I/O 검사 재시작) · 캠데코 비전검사기 연동은 현 범위."),
 ("C5","설비·툴 (Equipment/Tool)","설비보전계획/지시·설비보전이력·설비점검이력·툴사용실적·툴보전오더·툴PM실적·예비품(운용)","설비·금형의 점검·보전(고객 EAM 미보유 → MES 경량 보유 결정 유지). 툴·지그 마스터는 MES 정본(C1). ※ 명세서 47건에 보전 요구 부재 — 범위 재확인 필요(E25)."),
 ("C6","물류·재고 (Logistics/Inventory)","입하(발주/거래명세서·초과 검증)·입고·출고요청(자동 발행 ✓)·출고(부분출고·FIFO 옵션)·재고(생산창고·호퍼 포함)·출하지시(고객사 지시서 import ✓)·출하·반품·재작업·폐기(품의+기타출고 ✓)·재고이동(전수 기록)·재고실사·Picking&Packing·포장합병분할","창고·물류 트랜잭션. 출하 상위지시=고객사 지시서(D+1·시간대별 ✓) · 폐기=품의 후 기타 출고(✓) · 재생재는 ERP 동기화 제외 구역."),
]

CSS="""
*{box-sizing:border-box}html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;color:#14171a;font-size:11pt;line-height:1.45;margin:0;background:#fff}
.wrap{max-width:900px;margin:0 auto;padding:18px 22px}
h1{font-size:18pt;margin:0 0 2px}.sub{color:#5b6168;font-size:10pt;margin-bottom:10px}
.badge-conf{display:inline-block;border:1.5px solid #C9252C;color:#C9252C;font-weight:700;font-size:8.5pt;padding:1px 7px;border-radius:3px;letter-spacing:.5px}
.note{background:#f4f5f6;border:1px solid #dfe3e6;border-radius:5px;padding:9px 12px;margin:10px 0;font-size:9.6pt}
h2{font-size:13pt;margin:22px 0 6px;padding:7px 11px;background:#2b3036;color:#fff;border-radius:5px}
h3{font-size:11pt;margin:14px 0 4px;color:#14171a;border-left:4px solid #4758A9;padding-left:8px}
table{border-collapse:collapse;width:100%;font-size:9.7pt;margin:3px 0 0}
th,td{border:1px solid #d4d8db;padding:5px 8px;vertical-align:top;text-align:left}
th{background:#eef1f4;font-weight:700;font-size:8.8pt}
td.code{font-weight:700;color:#4758A9;white-space:nowrap;width:52px;text-align:center}
td.st{white-space:nowrap;width:48px;text-align:center;color:#1F883D;font-weight:700;font-size:8.6pt}
td.st.p{color:#E8A100}
td.rel{font-size:8.4pt;color:#6b7177}
td.cl{font-weight:700;color:#4758A9;white-space:nowrap;width:46px;text-align:center}
.foot{margin-top:22px;padding-top:10px;border-top:1px solid #dfe3e6;color:#6b7177;font-size:8.5pt}
@media print{.wrap{max-width:none;padding:0}h2{page-break-after:avoid}table{page-break-inside:auto}tr{page-break-inside:avoid}}
@page{size:A4;margin:13mm 12mm}
"""

P=[f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>OMF MES 코드 참조</title><style>{CSS}</style></head><body><div class="wrap">']
P.append(f'''<div><span class="badge-conf">CONFIDENTIAL · 대외비</span></div>
<h1>OMF MES 현장 점검 — 코드 참조</h1>
<div class="sub">질문지 v2 미결코드 · 데이터모델 v2 클러스터 · 요구사항 명세서 v1.1(2026-07-01) 반영 · 작성일 2026-07-03 · CREFLE OMF 팀</div>
<div class="note"><b>용도.</b> 현장 점검 체크리스트의 <b>② 미결</b> 블록에 나오는 코드(A1·D8·E5 등)와 본문의 클러스터(C1~C6)를 해설한다.
<b>미결코드</b> = 질문지 항목(알파벳=섹션, 숫자=순번) · <b>E 섹션</b> = 요구사항 명세서 발 후속 확인(고객 액션 회수 + 신규 미결) · <b>클러스터</b> = 데이터모델 6대 묶음.
<br>※ <b>S#</b> = 워크플로우 단계 번호(예: S10=10번째 단계, 미결코드 아님) · <b>종합N</b> = 데이터모델 §8 미결 종합 번호.
<br>※ <b>C1~C6</b>은 클러스터(아래 2장)이며, 질문지 C섹션(C1~C5)과 기호가 같아 문맥으로 구분한다. <b>✓ 확정</b>(2026-06-24~07-01) · <b>부분</b> = 부분확정(잔여 미결 병기).</div>''')

# 1. 미결코드
P.append('<h2>1. 질문지 미결코드 (A · B · C · D · E)</h2>')
for sec in ["A","B","C","D","E"]:
    if not rows[sec]: continue
    P.append(f'<h3>{SECT[sec]}</h3>')
    P.append('<table><tr><th>코드</th><th>상태</th><th>요지</th><th>관련</th></tr>')
    for code,n,st,q,rel in rows[sec]:
        cls="st p" if st=="부분" else "st"
        P.append(f'<tr><td class="code">{code}</td><td class="{cls}">{st}</td><td>{html.escape(q)}</td><td class="rel">{html.escape(rel)}</td></tr>')
    P.append('</table>')

# 2. 클러스터
P.append('<h2>2. 데이터모델 클러스터 (C1 ~ C6)</h2>')
P.append('<table><tr><th>클러스터</th><th>이름</th><th>주요 엔티티</th><th>역할</th></tr>')
for cid,name,ent,role in CLUSTERS:
    P.append(f'<tr><td class="cl">{cid}</td><td style="white-space:nowrap;font-weight:600">{html.escape(name)}</td><td style="font-size:9.2pt">{html.escape(ent)}</td><td style="font-size:9pt;color:#3e4146">{html.escape(role)}</td></tr>')
P.append('</table>')

tot=sum(len(rows[k]) for k in rows)
P.append(f'<div class="foot">미결코드 {tot}개(A {len(rows["A"])}·B {len(rows["B"])}·C {len(rows["C"])}·D {len(rows["D"])}·E {len(rows["E"])}) · 클러스터 6개 · 대외비(외부 공유·게시 금지). 근거: research/2026-07-03-현장검증-질문지-v2-요구사항통합.md · 2026-07-03-개념데이터모델-v2-요구사항통합.md · 2026-07-03-MES-요구사항-명세서-v1-정리.md</div>')
P.append('</div></body></html>')
open(OUT,"w",encoding="utf-8").write("\n".join(P))
print("WROTE",OUT)
for k in ["A","B","C","D","E"]: print(" ",k,len(rows[k]),"codes")

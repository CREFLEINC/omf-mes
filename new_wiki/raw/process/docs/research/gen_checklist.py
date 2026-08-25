# -*- coding: utf-8 -*-
import re, glob, html, os

BASE = "/Users/rangkim/projects/crefle/ohmyfactory/apps/omf/docs/research"
OUT  = os.path.join(BASE, "2026-07-03-현장점검-체크리스트.html")

# (표시ID, 표시명, 그룹, 원본번호, slice)  — 처리 순서대로. 02는 계획/실행 분리.
DOMAINS = [
    ("06",  "기준정보·연계", "전제",      "06", None),
    ("01",  "자재 창고",     "주 흐름",   "01", None),
    ("02A", "생산 계획",     "주 흐름",   "02", (0,4)),
    ("02B", "생산 실행",     "주 흐름",   "02", (4,None)),
    ("03",  "품질 관리",     "주 흐름",   "03", None),
    ("04",  "제품 출하",     "주 흐름",   "04", None),
    ("05",  "설비·툴",       "상시 지원", "05", None),
]

PROC_KEYS  = ["trigger","actor","action","input","result","rule"]
PROC_LABEL = {
    "trigger":"Trigger · 촉발","actor":"Actor · 주체","action":"Action · 행위",
    "input":"Input · 입력","result":"Result · 결과","rule":"Rule · 선행조건·규칙",
}
ROLES = ["생산관리","품질","설비","물류","전산","현장"]

def keyof(label):
    l=label.strip()
    for k,pat in [("trigger","Trigger"),("actor","Actor"),("action","Action"),
                  ("input","Input"),("medium","Medium"),("result","Result"),
                  ("rule","Rule"),("exception","Exception"),("pain","Pain"),
                  ("boundary","Boundary"),("openissue","Open-Issue"),("check","Check")]:
        if l.startswith(pat) or l.startswith("["+pat): return k
    return None

def inline(t):
    t=html.escape(t)
    t=re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",t)
    t=re.sub(r"\*(.+?)\*",r"<em>\1</em>",t)
    t=re.sub(r"`(.+?)`",r"<code>\1</code>",t)
    return t

def parse(num):
    path=glob.glob(os.path.join(BASE,f"2026-07-03-워크플로우-요구사항반영-{num}-*.md"))[0]
    steps=[]; cur=None
    for ln in open(path,encoding="utf-8").read().splitlines():
        ms=re.match(r"^##\s+S(\d+)\.\s*(.+)$",ln)
        if ms:
            if cur: steps.append(cur)
            cur={"no":"S"+ms.group(1),"title":ms.group(2).strip(),"f":{}}
            continue
        if cur is None: continue
        mf=re.match(r"^-\s+\*\*(.+?)\*\*\s*([🟡🟠🔗⚠\s]*?):\s*(.*)$",ln)
        if mf:
            k=keyof(mf.group(1))
            if k: cur["f"][k]=mf.group(3).strip()
    if cur: steps.append(cur)
    return steps

def role_of(t):
    r=set()
    if "생산관리" in t: r.add("생산관리")
    if "품질" in t: r.add("품질")
    if "설비" in t: r.add("설비")
    if "물류" in t or "창고" in t: r.add("물류")
    if "전산" in t or "ERP" in t: r.add("전산")
    if "현장반장" in t or "작업자" in t or "반장" in t: r.add("현장")
    return r

def short(title):
    t=re.split(r"[/·(]",title)[0].strip()
    return t[:13]

def split_dot(t):
    t=re.sub(r"^⚠\s*","",t)
    p=[x.strip(" ·.") for x in re.split(r"\s·\s|·",t) if x.strip(" ·.")]
    return p if len(p)>1 else [t.strip()]

def split_excl(t):
    s=[x.strip() for x in re.split(r"(?=[①②③④⑤⑥⑦⑧⑨])",t) if x.strip()]
    return s if s else [t.strip()]

# load
src={}
data=[]
for did,name,grp,num,sl in DOMAINS:
    if num not in src: src[num]=parse(num)
    steps=src[num] if sl is None else src[num][sl[0]:sl[1]]
    data.append((did,name,grp,steps))

matrix={did:set().union(*[role_of(s["f"].get("actor","")) for s in steps]) if steps else set()
        for did,name,grp,steps in data}

CSS="""
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;color:#14171a;font-size:11pt;line-height:1.45;margin:0;background:#fff}
.wrap{max-width:920px;margin:0 auto;padding:18px 22px}
h1{font-size:19pt;margin:0 0 2px}
.sub{color:#5b6168;font-size:10pt;margin-bottom:10px}
.badge-conf{display:inline-block;border:1.5px solid #C9252C;color:#C9252C;font-weight:700;font-size:8.5pt;padding:1px 7px;border-radius:3px;letter-spacing:.5px}
.note{background:#f4f5f6;border:1px solid #dfe3e6;border-radius:5px;padding:10px 13px;margin:10px 0;font-size:10pt}
.legend{font-size:9.5pt;color:#3e4146;margin:8px 0 0}.legend span{display:inline-block;margin-right:14px}
table.mtx{border-collapse:collapse;width:100%;font-size:9.5pt;margin:6px 0 0}
table.mtx th,table.mtx td{border:1px solid #d4d8db;padding:4px 6px;text-align:center}
table.mtx th{background:#2b3036;color:#fff;font-weight:600}
table.mtx td.dom{text-align:left;font-weight:600;background:#f4f5f6;white-space:nowrap}
.dot{color:#1F883D;font-weight:700}
.domain{margin-top:26px}
.domain-h{background:#2b3036;color:#fff;padding:8px 12px;border-radius:5px 5px 0 0;font-size:13pt;font-weight:700;display:flex;justify-content:space-between;align-items:center}
.domain-h .grp{font-size:9pt;font-weight:500;opacity:.85;border:1px solid rgba(255,255,255,.4);padding:1px 7px;border-radius:10px}
.dflow{display:flex;flex-wrap:wrap;align-items:center;gap:4px 2px;padding:10px 12px;background:#eef1f4;border:1px solid #d4d8db;border-top:none}
.dflow .fn{background:#fff;border:1px solid #b9c0c6;border-radius:4px;padding:3px 8px;white-space:nowrap;font-size:8.8pt}
.dflow .fn .n{color:#4758A9;font-weight:700;margin-right:4px}
.dflow .ar{color:#9aa1a8;font-weight:700;padding:0 2px;font-size:10pt}
.step{border:1px solid #cfd4d8;border-top:none;padding:11px 13px}
.step:last-child{border-radius:0 0 5px 5px}
.crumb{display:flex;flex-wrap:wrap;gap:3px;margin:0 0 8px}
.crumb .c{color:#9aa1a8;border:1px solid #dfe3e6;border-radius:9px;padding:0 6px;background:#f7f8f9;font-size:7.6pt;line-height:1.7}
.crumb .c.cur{color:#fff;background:#4758A9;border-color:#4758A9;font-weight:700}
.step-h{font-size:11.5pt;font-weight:700;margin:0 0 8px;padding-bottom:5px;border-bottom:2px solid #2b3036}
.step-h .bdg{display:inline-block;background:#4758A9;color:#fff;font-size:9pt;font-weight:700;padding:1px 7px;border-radius:3px;margin-right:7px;vertical-align:1px}
.sechd{font-size:8.6pt;font-weight:700;color:#5b6168;letter-spacing:.4px;margin:0 0 3px;text-transform:uppercase}
table.proc{border-collapse:collapse;width:100%;margin:0 0 9px}
table.proc th{width:118px;text-align:left;vertical-align:top;color:#3e4146;font-size:8.7pt;font-weight:700;padding:3px 8px 3px 0;border-bottom:1px solid #eef0f2;white-space:nowrap}
table.proc td{vertical-align:top;padding:3px 0;border-bottom:1px solid #eef0f2;font-size:10pt}
.checkwrap .sechd{margin-top:2px}
.ckblock{border-left:3px solid #ccc;padding:5px 10px;margin:5px 0 0;background:#fafbfc;border-radius:0 4px 4px 0}
.ckblock.pt{border-color:#4758A9;background:#f5f7fb}
.ckblock.oi{border-color:#E8A100;background:#fdf8ef}
.ckblock.ex{border-color:#B3261E;background:#fcf2f1}
.ckhd{font-size:8.9pt;font-weight:700;margin:0 0 3px;color:#14171a}
ul.cks{list-style:none;margin:1px 0 0;padding:0}
ul.cks li{position:relative;padding:2px 0 2px 22px;font-size:9.6pt;line-height:1.4}
ul.cks li::before{content:"";position:absolute;left:0;top:3px;width:12px;height:12px;border:1.4px solid #6b7177;border-radius:2px;background:#fff}
.ref{font-size:8.8pt;color:#6b7177;margin:8px 0 0;line-height:1.45;border-top:1px dotted #dfe3e6;padding-top:6px}
.ref b{color:#4a5056}
.memo{margin:7px 0 0;border:1px dashed #b9c0c6;border-radius:4px;min-height:34px;padding:4px 8px}
.memo .ml{font-size:8pt;color:#9aa1a8}
.foot{margin-top:24px;padding-top:10px;border-top:1px solid #dfe3e6;color:#6b7177;font-size:8.5pt}
@media print{.wrap{max-width:none;padding:0}.domain{page-break-before:always}.step{page-break-inside:avoid}.note,.ckblock,.memo,.dflow{page-break-inside:avoid}}
@page{size:A4;margin:13mm 12mm}
"""

P=[]
P.append(f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OMF MES 현장 점검 체크리스트</title><style>{CSS}</style></head><body><div class="wrap">')
P.append(f'''
<div><span class="badge-conf">CONFIDENTIAL · 대외비</span></div>
<h1>OMF MES 현장 점검 체크리스트</h1>
<div class="sub">삼진엘앤디 비나 법인 · STEP3 현장 검증 — 요구사항 명세서 v1.1(2026-07-01) 반영판 · 작성일 2026-07-03 · 작성 CREFLE OMF 팀</div>
<div class="note"><b>사용법.</b> 각 단계는 <b>절차(현재 어떻게 도는가)</b>와 <b>현장 확인(3블록 체크박스)</b>으로 구성된다. 절차 6필드(Trigger·Actor·Action·Input·Result·Rule)는 단계의 정의, 체크박스는 현장에서 <b>관찰·질문·수집</b>할 항목이다. 도메인 머리의 흐름도와 각 단계의 위치표시로 진행 지점을 확인한다. ☐를 채우고 메모에 결과를 적는다.<br><b>전제.</b> ✅ 표시는 <em>요구사항 명세서(2026-07-01)로 검증·확정된 사실</em>, 🟡는 <em>현행 추정(가설)</em>으로 현장 반증(확인) 대상. 벤더 To-Be 기준 아님.</div>
<div class="legend"><span>☐ <b>① 확인 포인트</b>=관찰·질문</span><span>☐ <b>② 미결</b>=질문지 확정</span><span>☐ <b>③ 예외</b>=선행조건 깨질 때</span><span>🔗 경계=시스템·부서 넘는 지점</span></div>
<div class="note" style="font-size:9.3pt"><b>미결 코드 체계(②·🔗 참조).</b> <b>알파벳=질문지 섹션, 숫자=항목 순번</b> — <b>A</b> LOT·추적 · <b>B</b> 엔티티 키·정규화 · <b>C</b> 소유 경계 · <b>D</b> 범위·보완 · <b>E</b> 요구사항 발 후속 확인(질문지 v2 신설). (예: <b>A1</b>=자재LOT 발번 주체, <b>D8</b>=WorkCalendar 귀속, <b>E5</b>=고객사 지시서 샘플)<br>※ <b>종합N</b>=데이터모델 §8 미결 종합 번호 · <b>C1~C6</b>=데이터모델 클러스터(C섹션 질문번호와 문맥으로 구분).</div>
<div class="note"><b>처리 순서(권장 동선).</b> ⑥ 기준정보(전제) → ① 자재 입고 → ②A 생산계획 → ②B 생산실행 → ③ 품질 → ④ 제품 출하 → ⑤ 설비·툴(상시).
<table class="mtx"><tr><th>도메인(단계 수)</th>{"".join(f"<th>{r}</th>" for r in ROLES)}<th>구분</th></tr>''')
for did,name,grp,steps in data:
    cells="".join(f'<td>{"<span class=dot>●</span>" if r in matrix[did] else ""}</td>' for r in ROLES)
    P.append(f'<tr><td class="dom">{did} {html.escape(name)} ({len(steps)})</td>{cells}<td>{html.escape(grp)}</td></tr>')
P.append('</table><div style="font-size:8.5pt;color:#6b7177;margin-top:4px">● = 해당 역할 동석 권장</div></div>')

for did,name,grp,steps in data:
    P.append(f'<div class="domain"><div class="domain-h"><span>{did} · {html.escape(name)}</span><span class="grp">{html.escape(grp)} · {len(steps)}단계</span></div>')
    # 흐름도
    fl=[]
    for i,s in enumerate(steps):
        if i: fl.append('<span class="ar">→</span>')
        fl.append(f'<span class="fn"><span class="n">{s["no"]}</span>{html.escape(short(s["title"]))}</span>')
    P.append('<div class="dflow">'+"".join(fl)+'</div>')
    # 단계 카드
    for idx,s in enumerate(steps):
        f=s["f"]
        crumb="".join(f'<span class="c{" cur" if j==idx else ""}">{st["no"]}</span>' for j,st in enumerate(steps))
        P.append(f'<div class="step"><div class="crumb">{crumb}</div>')
        P.append(f'<div class="step-h"><span class="bdg">{s["no"]}</span>{html.escape(s["title"])}</div>')
        P.append('<div class="sechd">절차</div><table class="proc">')
        for k in PROC_KEYS:
            if f.get(k): P.append(f'<tr><th>{PROC_LABEL[k]}</th><td>{inline(f[k])}</td></tr>')
        P.append('</table>')
        P.append('<div class="checkwrap"><div class="sechd">✔ 현장 확인</div>')
        if f.get("check"):
            it="".join(f"<li>{inline(x)}</li>" for x in split_dot(f["check"]))
            P.append(f'<div class="ckblock pt"><div class="ckhd">① 확인 포인트 (관찰·질문)</div><ul class="cks">{it}</ul></div>')
        if f.get("openissue"):
            it="".join(f"<li>{inline(x)}</li>" for x in split_dot(f["openissue"]))
            P.append(f'<div class="ckblock oi"><div class="ckhd">② 미결 확정 (질문지)</div><ul class="cks">{it}</ul></div>')
        if f.get("exception"):
            it="".join(f"<li>{inline(x)}</li>" for x in split_excl(f["exception"]))
            P.append(f'<div class="ckblock ex"><div class="ckhd">③ 예외 점검 (선행조건 미충족)</div><ul class="cks">{it}</ul></div>')
        P.append('</div>')
        refs=[]
        if f.get("medium"): refs.append(f'<b>매체(현행추정):</b> {inline(f["medium"])}')
        if f.get("pain"): refs.append(f'<b>예상 Pain:</b> {inline(f["pain"])}')
        if f.get("boundary"): refs.append(f'<b>🔗 경계:</b> {inline(f["boundary"])}')
        if refs: P.append('<div class="ref">'+" &nbsp;·&nbsp; ".join(refs)+'</div>')
        P.append('<div class="memo"><span class="ml">관찰·결과 메모</span></div></div>')
    P.append('</div>')

tot=sum(len(s) for *_,s in data)
P.append(f'<div class="foot">총 {len(DOMAINS)}개 도메인 · {tot}개 단계 · 대외비(외부 공유·게시 금지). 근거: research/2026-07-03-워크플로우-요구사항반영-01~06 (요구사항 명세서 v1.1 통합) · 질문지 v2.</div></div></body></html>')
open(OUT,"w",encoding="utf-8").write("\n".join(P))
print("WROTE",OUT,"| domains",len(DOMAINS),"steps",tot)
for did,name,grp,steps in data: print(" ",did,name,len(steps))

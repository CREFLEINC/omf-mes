# -*- coding: utf-8 -*-
"""화면 목록·IA 도식본 — 단일 HTML(외부 asset 0) 생성."""
import io, json, sys

ROWS = json.load(io.open(sys.argv[1], encoding='utf-8'))
OUT  = sys.argv[2]

NEW  = {'M-04-04','W-06-13','W-CO-08'}
GONE = [('M-01-03','IQC 대상 LOT 스캔','mob','01-S-C 전체 웹 확정 → W-01-01 병합'),
        ('M-04-02','피킹 대상 목록','mob','목록 진입 경로 기준 → M-04-01 통합'),
        ('W-03-06','불량·부적합 판정·폐기 품의','web','03 co-locate 위반 · 소유 엔티티 0 — 판정은 검사 화면, 품의는 도메인 품의 화면으로 이미 갈림'),
        ('W-03-07','SPC 관제 대시보드','web','결정 11이 Analytics 단계로 이연 명시 — 삭제가 아니라 <b>이관</b>'),
        ('W-01-08','위치 확인 모니터링','web','<b>v1.3</b> · REQ-PR-0005는 「자재 LOT 적재 <b>위치 정보 관리</b>」 요구 → W-01-07 재고 현황·상태 조회에 <b>위치별 분포 뷰</b>로 흡수'),
        ('W-02-09','생산 현황·비가동 알람 대시보드','web','<b>v1.3</b> · REQ-PR-0016은 <b>알람</b> 요구 → 알람은 W-CO-03 알림센터 · 생산 실적 집계는 W-02-08 · 일일생산실적은 W-CO-05'),
        ('W-03-08','품질 대시보드·불량 발생 알람','web','<b>v1.3</b> · 동상 → 알람은 W-CO-03 · <b>불량률·불량코드 분포 집계</b>는 W-03-05'),
        ('W-04-09','출하 현황 모니터링 대시보드','web','<b>v1.3</b> · QA #21 「현행 모니터링 없음 · <b>추후</b> 고객 요구」 = 아직 요구가 아님 → W-04-02 출하 예정 목록 · W-04-08 완제품 재고 조회'),
        ('W-05-14','설비·툴 대시보드','web','<b>v1.3</b> · REQ-PR-0036 하나가 화면 둘을 정당화하지 못한다 → W-CO-05 통합 · 가동률/OEE는 W-05-08 · PM 도래는 W-05-02')]

NAME = {r[0]: r[1] for r in ROWS}

# ── 업무 흐름 8단계 × 3레인 (자재→제품 축)
STAGES = [
 ('입하',      '01', {'mob':['M-01-01','M-01-02','M-01-06'], 'pop':['P-01-01'], 'web':['W-01-09','W-01-03','W-01-11']}),
 ('수입검사',  '01', {'mob':[], 'pop':[], 'web':['W-01-01','W-01-02','W-01-10']}),
 ('적치·보관', '01', {'mob':['M-01-04','M-01-05','M-01-07'], 'pop':[], 'web':['W-01-07']}),
 ('출고·투입', '01', {'mob':['M-01-08','M-01-09','M-01-12'], 'pop':['P-01-02'], 'web':['W-02-10']}),
 ('생산 계획', '02', {'mob':[], 'pop':[], 'web':['W-02-01','W-02-02','W-02-03','W-02-04','W-02-06','W-02-07']}),
 ('생산 실행', '02', {'mob':['M-02-01','M-02-02'], 'pop':['P-CO-01','P-02-01','P-02-02','P-02-03','P-02-04','P-02-06','P-02-10','P-02-11','P-02-12'], 'web':['W-02-08']}),
 ('검사·포장', '02·03·04', {'mob':['M-04-03'], 'pop':['P-02-13','P-02-05','P-02-07','P-02-08','P-02-09','P-04-04','P-04-03'], 'web':['W-03-01','W-03-02','W-03-03','W-03-09','W-04-03']}),
 ('출하',      '04', {'mob':['M-04-01','M-04-04'], 'pop':['P-04-01','P-04-02'], 'web':['W-04-01','W-04-02','W-04-04','W-04-05','W-02-05']}),
]
# 흐름 밖 — 예외·역방향·지원
BANDS = [
 ('예외·역흐름', '반품 · 폐기 · 재고조정 · 재작업', {'mob':['M-01-10','M-01-11'], 'pop':[], 'web':['W-01-04','W-01-12','W-01-05','W-01-06','W-04-06','W-04-11','W-04-07','W-04-10']}),
 ('설비·툴 (05)', '점검 · 보전 · 비가동 · 계측', {'mob':['M-05-01','M-05-02'], 'pop':['P-05-01','P-05-02'], 'web':['W-05-01','W-05-02','W-05-03','W-05-04','W-05-05','W-05-06','W-05-07','W-05-08','W-05-09','W-05-10','W-05-11','W-05-12','W-05-13']}),
 ('기준정보·연계 (06)', '마스터 · Rev · I/F', {'mob':[], 'pop':[], 'web':['W-06-01','W-06-02','W-06-03','W-06-04','W-06-05','W-06-06','W-06-07','W-06-08','W-06-09','W-06-10','W-06-11','W-06-12','W-06-13']}),
 ('공통 (CO)', '계정 · 알림 · 대시보드 · 설정', {'mob':['M-CO-01'], 'pop':[], 'web':['W-CO-01','W-CO-02','W-CO-03','W-CO-04','W-CO-05','W-CO-06','W-CO-08']}),
 ('조회', '전 도메인 (도식 앵커 밖 · 별도 트랙 18건에 다수 포함 · v1.3에서 대시보드 5건이 빠져 순수 조회만 남았다)', {'mob':[], 'pop':[], 'web':['W-03-04','W-03-05','W-04-08']}),
]

def chip(sid):
    if sid not in NAME: return ''
    prog = {'W':'web','P':'pop','M':'mob'}[sid[0]]
    cls  = 'chip ' + prog + (' new' if sid in NEW else '')
    return '<span class="%s" data-id="%s"><b>%s</b>%s</span>' % (cls, sid, sid, NAME[sid])

def lane(d, k):
    return ''.join(chip(x) for x in d.get(k, [])) or '<span class="none">—</span>'

# ── 매트릭스
DOMS = [('01','자재창고관리'),('02','생산실행'),('03','품질관리'),('04','제품출하'),
        ('05','설비·툴 관리'),('06','기준정보·연계'),('CO','공통')]
mat = {}
for r in ROWS: mat[(r[6], r[5])] = mat.get((r[6], r[5]), 0) + 1
mx = max(mat.values())

mrows = []
for d, dn in DOMS:
    tds = []
    for p in ('web','pop','mob'):
        v = mat.get((d,p), 0)
        lv = 0 if not v else 1 + int(3.99 * v / mx)
        tds.append('<td class="hm %s l%d">%s</td>' % (p, lv, v or '·'))
    tot = sum(mat.get((d,p),0) for p in ('web','pop','mob'))
    mrows.append('<tr><th>%s<span>%s</span></th>%s<td class="tot">%d</td></tr>' % (d, dn, ''.join(tds), tot))
mtot = ''.join('<td class="tot">%d</td>' % sum(mat.get((d,p),0) for d,_ in DOMS) for p in ('web','pop','mob'))

# ── 관리웹 메뉴 트리
TREE = [
 ('기준정보', [('마스터', ['W-06-01','W-06-05','W-06-06','W-06-07','W-06-08','W-06-11']),
              ('품질 기준', ['W-06-02','W-06-03','W-06-04','W-06-13']),
              ('연계(I/F)', ['W-06-09','W-06-12','W-06-10'])]),
 ('생산',     [('계획·지시', ['W-02-01','W-02-02','W-02-03','W-02-04','W-02-07','W-02-06','W-02-10']),
              ('마감·모니터링', ['W-02-05','W-02-08'])]),
 ('품질',     [('Lot Status', ['W-03-01','W-03-02','W-03-03','W-03-04','W-03-09']),
              ('검사·불량', ['W-03-05'])]),
 ('자재/창고', [('입하·검사', ['W-01-09','W-01-01','W-01-10','W-01-02','W-01-03','W-01-11']),
              ('재고·출고', ['W-01-07','W-01-04','W-01-12']),
              ('반품·폐기', ['W-01-05','W-01-06'])]),
 ('출하',     [('출하 지시·확정', ['W-04-01','W-04-02','W-04-03','W-04-04','W-04-05']),
              ('반품·재고', ['W-04-06','W-04-11','W-04-07','W-04-08','W-04-10'])]),
 ('설비/툴',  [('툴 관리', ['W-05-01','W-05-02','W-05-03','W-05-13']),
              ('설비 보전', ['W-05-04','W-05-05','W-05-06','W-05-12']),
              ('비가동·계측', ['W-05-08','W-05-09','W-05-07','W-05-10','W-05-11'])]),
 ('시스템/공통', [('계정·권한', ['W-CO-01','W-CO-02']), ('알림·공지', ['W-CO-03','W-CO-04']),
              ('설정', ['W-CO-06','W-CO-08']), ('경영 대시보드', ['W-CO-05'])]),
]
tree_html = ''.join(
  '<div class="t1"><h4>%s</h4>%s</div>' % (top, ''.join(
     '<div class="t2"><span class="t2n">%s</span><div class="t3">%s</div></div>' % (g, ''.join(chip(x) for x in ids))
     for g, ids in groups))
  for top, groups in TREE)

# ── POP 태스크 흐름
POP_FLOW = [
 ('진입',        ['P-CO-01','P-02-01']),
 ('작업 전 게이트', ['P-02-02']),
 ('생산 실행',    ['P-02-03','P-02-04','P-02-13','P-02-06']),
 ('라벨·인식표',  ['P-02-05','P-02-07']),
 ('포장·출하',    ['P-02-08','P-02-09','P-04-01','P-04-02','P-04-04','P-04-03']),
 ('예외·긴급',    ['P-02-10','P-02-11','P-02-12']),
 ('창고 스테이션', ['P-01-01','P-01-02']),
 ('설비 수집',    ['P-05-01','P-05-02']),
]
pop_html = ''.join('<div class="pstep"><span class="pn">%s</span><div>%s</div></div>' % (n, ''.join(chip(x) for x in ids)) for n, ids in POP_FLOW)

# ── 모바일 타일
TILES = [('📦','입하',['M-01-01','M-01-02','M-01-06']), ('📥','적치',['M-01-04','M-01-05','M-01-07']),
         ('📤','피킹/출고',['M-01-08','M-01-09']), ('♻️','재생재',['M-01-12']),
         ('🔀','이동',['M-01-10']), ('🧮','실사',['M-01-11']),
         ('🏭','생산 이동/수리',['M-02-01','M-02-02']), ('🚚','출하 스캔',['M-04-01','M-04-04','M-04-03']),
         ('🛠','설비',['M-05-01','M-05-02'])]
tile_html = ''.join('<div class="tile"><span class="ic">%s</span><span class="tn">%s</span><div>%s</div></div>' % (i, n, ''.join(chip(x) for x in ids)) for i, n, ids in TILES)

gone_html = ''.join('<div class="gone"><span class="chip %s %s"><b>%s</b>%s</span><p>%s</p></div>'
                    % (p, 'moved' if '이관' in r else 'del', i, n_, r) for i, n_, p, r in GONE)
new_html  = ''.join('<div class="gone"><span class="chip %s new"><b>%s</b>%s</span><p>%s</p></div>' % (
    {'W':'web','P':'pop','M':'mob'}[i[0]], i, NAME[i], r) for i, r in [
    ('W-01-10','배지 사각지대 해소 — IQC 생략 경로가 화면 없이 Release되던 공백'),
    ('W-01-11','관리웹 절단 = 저장 엔티티 (W-01-03에서 분리 · ERP 전표+승인 마커)'),
    ('W-01-12','관리웹 절단 = 저장 엔티티 (W-01-04에서 분리 · ERP 조정 전표)'),
    ('W-04-11','작업 끊김 — 반품입고와 사이에 03 판정·재작업이 낀다 (W-04-06에서 분리)'),
    ('M-01-12','모바일 독립 진입 — 출고분 입고와 무관한 사건 (M-01-09에서 분리)')])

DOC = io.open(OUT, 'w', encoding='utf-8')
DOC.write('''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>화면 목록 · IA 도식본 (v1.3)</title>
<style>
*,*::before,*::after{box-sizing:border-box}
:root{
 --bg:#f6f7f9; --card:#fff; --ink:#16181d; --dim:#5c6270; --line:#e3e6ec;
 --web:#2F6FED; --pop:#F2994A; --mob:#27AE60;
 --webbg:#eaf1fe; --popbg:#fef2e6; --mobbg:#e8f7ee;
 --new:#7c3aed; --del:#c2410c;
}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--ink:#e8eaf0;--dim:#98a0b0;--line:#272c36;
 --webbg:#16233d;--popbg:#33240f;--mobbg:#10291b}}
:root[data-theme=dark]{--bg:#0f1115;--card:#171a21;--ink:#e8eaf0;--dim:#98a0b0;--line:#272c36;
 --webbg:#16233d;--popbg:#33240f;--mobbg:#10291b}
:root[data-theme=light]{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--dim:#5c6270;--line:#e3e6ec;
 --webbg:#eaf1fe;--popbg:#fef2e6;--mobbg:#e8f7ee}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
 font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1240px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--dim);margin:0 0 28px;font-size:13px}
h2{font-size:17px;margin:44px 0 6px;letter-spacing:-.01em;display:flex;align-items:baseline;gap:10px}
h2 small{font-weight:400;font-size:12px;color:var(--dim);letter-spacing:0}
.lead{color:var(--dim);margin:0 0 16px;font-size:13px;max-width:80ch}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;overflow-x:auto}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:8px}
.kpi div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi b{display:block;font-size:28px;letter-spacing:-.03em;line-height:1.1}
.kpi span{font-size:11px;color:var(--dim)}
.chip{display:inline-flex;align-items:center;gap:6px;border-radius:7px;padding:4px 9px;margin:3px 4px 3px 0;
 font-size:12px;border:1px solid transparent;white-space:nowrap;cursor:default}
.chip b{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;font-weight:600;opacity:.85}
.chip.web{background:var(--webbg);color:var(--web);border-color:color-mix(in srgb,var(--web) 25%,transparent)}
.chip.pop{background:var(--popbg);color:#b26a1d;border-color:color-mix(in srgb,var(--pop) 35%,transparent)}
.chip.mob{background:var(--mobbg);color:#1d7a45;border-color:color-mix(in srgb,var(--mob) 30%,transparent)}
@media (prefers-color-scheme:dark){.chip.pop{color:#f0ad63}.chip.mob{color:#5ecb8c}.chip.web{color:#7ea9f7}}
.chip.new{box-shadow:0 0 0 2px color-mix(in srgb,var(--new) 45%,transparent)}
.chip.del{opacity:.55;text-decoration:line-through}
.chip.moved{opacity:.7;box-shadow:0 0 0 2px color-mix(in srgb,var(--del) 40%,transparent)}
.none{color:var(--dim);opacity:.5;font-size:12px}
.legend{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:0 0 14px;font-size:12px;color:var(--dim)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left}
thead th{background:color-mix(in srgb,var(--line) 40%,transparent);font-size:12px}
.hm{text-align:center;font-variant-numeric:tabular-nums;font-weight:600}
.hm.l0{color:var(--dim);opacity:.35;font-weight:400}
.hm.web.l1{background:color-mix(in srgb,var(--web) 8%,transparent)}.hm.web.l2{background:color-mix(in srgb,var(--web) 16%,transparent)}
.hm.web.l3{background:color-mix(in srgb,var(--web) 26%,transparent)}.hm.web.l4{background:color-mix(in srgb,var(--web) 38%,transparent);color:#fff}
.hm.pop.l1{background:color-mix(in srgb,var(--pop) 10%,transparent)}.hm.pop.l2{background:color-mix(in srgb,var(--pop) 20%,transparent)}
.hm.pop.l3{background:color-mix(in srgb,var(--pop) 32%,transparent)}.hm.pop.l4{background:color-mix(in srgb,var(--pop) 46%,transparent)}
.hm.mob.l1{background:color-mix(in srgb,var(--mob) 9%,transparent)}.hm.mob.l2{background:color-mix(in srgb,var(--mob) 18%,transparent)}
.hm.mob.l3{background:color-mix(in srgb,var(--mob) 28%,transparent)}.hm.mob.l4{background:color-mix(in srgb,var(--mob) 40%,transparent)}
td.tot,th.tot{font-weight:700;font-variant-numeric:tabular-nums;text-align:center}
table th:first-child span{display:block;font-weight:400;font-size:11px;color:var(--dim)}
.flow{min-width:940px}
.frow{display:grid;grid-template-columns:120px 1fr;gap:0;border-bottom:1px solid var(--line)}
.frow:last-child{border-bottom:0}
.fst{padding:12px 10px 12px 0;border-right:2px solid var(--line);position:relative}
.fst b{display:block;font-size:13px}.fst span{font-size:11px;color:var(--dim)}
.fst::after{content:"";position:absolute;right:-5px;top:50%;width:8px;height:8px;border-radius:50%;background:var(--line)}
.flanes{display:grid;grid-template-rows:repeat(3,auto)}
.fl{display:grid;grid-template-columns:56px 1fr;align-items:center;gap:8px;padding:5px 0 5px 12px;border-bottom:1px dashed color-mix(in srgb,var(--line) 70%,transparent)}
.fl:last-child{border-bottom:0}
.fl>i{font-style:normal;font-size:10px;font-weight:700;letter-spacing:.04em;text-align:right;opacity:.7}
.fl.web>i{color:var(--web)}.fl.pop>i{color:#b26a1d}.fl.mob>i{color:#1d7a45}
.band{border-left:3px solid var(--line);padding-left:12px;margin-bottom:14px}
.band b{font-size:13px}.band em{font-style:normal;font-size:11px;color:var(--dim);margin-left:8px}
.t1{margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--line)}
.t1:last-child{border-bottom:0;margin-bottom:0;padding-bottom:0}
.t1 h4{margin:0 0 6px;font-size:13px}
.t2{display:grid;grid-template-columns:120px 1fr;gap:8px;align-items:start;padding:3px 0}
.t2n{font-size:11.5px;color:var(--dim);padding-top:7px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.pstep{border-left:2px solid var(--line);padding:0 0 14px 14px;position:relative}
.pstep:last-child{padding-bottom:0}
.pstep::before{content:"";position:absolute;left:-6px;top:6px;width:10px;height:10px;border-radius:50%;background:var(--pop)}
.pn{font-size:11.5px;color:var(--dim);display:block;margin-bottom:2px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.tile{background:var(--mobbg);border:1px solid color-mix(in srgb,var(--mob) 22%,transparent);border-radius:12px;padding:12px}
.tile .ic{font-size:19px;display:block}
.tile .tn{font-size:12px;font-weight:600;display:block;margin:2px 0 6px;color:#1d7a45}
@media (prefers-color-scheme:dark){.tile .tn{color:#5ecb8c}}
.gone{display:grid;grid-template-columns:280px 1fr;gap:12px;align-items:center;padding:8px 0;border-bottom:1px dashed var(--line)}
.gone:last-child{border-bottom:0}
.gone p{margin:0;font-size:12px;color:var(--dim)}
.ctl{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center}
.ctl button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;
 padding:5px 13px;font-size:12px;cursor:pointer;font-family:inherit}
.ctl button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.ctl input{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;
 padding:6px 11px;font-size:12px;min-width:180px;font-family:inherit}
#cnt{font-size:12px;color:var(--dim);margin-left:auto}
#tbl td:first-child{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;white-space:nowrap}
.pill{font-size:10.5px;padding:2px 7px;border-radius:99px;border:1px solid var(--line)}
.pill.확정{background:color-mix(in srgb,var(--mob) 14%,transparent)}
.pill.추정{background:color-mix(in srgb,var(--pop) 16%,transparent)}
.pill.미정{background:color-mix(in srgb,var(--del) 15%,transparent)}
.note{background:color-mix(in srgb,var(--web) 7%,transparent);border-left:3px solid var(--web);
 border-radius:0 8px 8px 0;padding:12px 14px;font-size:12.5px;margin:14px 0}
.note b{color:var(--web)}
.foot{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);font-size:11.5px;color:var(--dim)}
#top{position:fixed;right:18px;bottom:18px;border:1px solid var(--line);background:var(--card);color:var(--ink);
 border-radius:99px;padding:8px 14px;font-size:12px;cursor:pointer;font-family:inherit;box-shadow:0 2px 10px rgba(0,0,0,.08)}
@media print{body{background:#fff}.card{break-inside:avoid}#top,.ctl{display:none}}
</style></head><body><div class="wrap">

<h1>화면 목록 · IA 도식본</h1>
<p class="sub">CREFLE · OMF MES UI/UX · <b>v1.3</b> (2026-07-29) · 내부 대외비<br>
정본 = <code>screen-inventory-ia.md</code> v1.3 · 결정 근거 = <code>보류결정-확정기록.md</code> v1.4 · <code>비도식근거-적용결과.md</code> §2 · 판정 기준 = <code>screen-mapping-rule.md</code> v1.3</p>

<div class="kpi">
 <div><b>109</b><span>화면 &nbsp;·&nbsp; 관리웹 68 · POP 22 · 모바일 19</span></div>
 <div><b>3</b><span>프로그램 &nbsp;·&nbsp; IA 모델이 서로 다르다</span></div>
 <div><b>82</b><span>확정 &nbsp;·&nbsp; 추정 25 · 미정 2</span></div>
 <div><b>73</b><span>화면 그룹 &nbsp;·&nbsp; 도식 미대응 0</span></div>
 <div><b>−4</b><span>v1.2 대비 &nbsp;·&nbsp; 존치 21·삭제 6·통합 1·신설 3</span></div>
</div>

<div class="note"><b>이 문서를 읽는 법.</b> 화면 108건은 <b>도식(FigJam) 노드에서 도출</b>했지 창작하지 않았다.
아래 ① 흐름 도식이 「언제 어느 단말을 쓰는가」를 보여주고, ②는 도메인별 단말 편중, ③~⑤는 프로그램별 IA 모델,
⑥은 최근 변동, ⑦은 전체 목록이다. <span class="chip web new"><b>보라 테두리</b></span>는 v1.2 신설 화면.<br>
<b>v1.3 — 대시보드 6건 중 REQ가 직접 요구한 것은 <code>W-CO-05</code> 하나뿐</b>이었다(REQ-PR-0036). 나머지 5건의 근거였던 REQ-PR-0016은 「특정 이벤트에 대한 <b>알람</b>」 요구고, 알람은 SNS+<code>W-CO-03</code> 알림센터로 이미 확정돼 있다(QA #24). 5건을 삭제하고 집계 뷰는 도메인 조회 화면의 요건으로 못박았다.</div>

<h2>① 업무 흐름 × 단말 <small>자재 입하부터 제품 출하까지 · 3개 레인</small></h2>
<p class="lead">가로축은 업무가 흘러가는 순서, 세로 3줄은 프로그램이다. <b>현장 이동은 모바일, 라인 작업은 POP, 판정·전표는 웹</b>이라는 원칙이 눈에 보인다 — 이것이 배지 정본 65배치가 만든 구조다.</p>
<div class="legend">
 <span><i style="background:var(--web)"></i>관리웹 — 사무 PC · 판정 · 전표 · 마스터</span>
 <span><i style="background:var(--pop)"></i>POP — 산업용 패널 PC · 실적 · 스캔 · 라벨</span>
 <span><i style="background:var(--mob)"></i>모바일 — PDA · 창고 동선 스캔</span>
</div>
<div class="card"><div class="flow">''')

for name, dom, lanes in STAGES:
    DOC.write('<div class="frow"><div class="fst"><b>%s</b><span>%s</span></div><div class="flanes">'
              '<div class="fl web"><i>WEB</i><div>%s</div></div>'
              '<div class="fl pop"><i>POP</i><div>%s</div></div>'
              '<div class="fl mob"><i>MOBILE</i><div>%s</div></div>'
              '</div></div>' % (name, dom, lane(lanes,'web'), lane(lanes,'pop'), lane(lanes,'mob')))
DOC.write('</div></div>')

DOC.write('<h2>흐름 밖 — 예외 · 지원 도메인</h2><p class="lead">역방향(반품·폐기·조정)과 상시 지원(설비·기준정보·공통)은 위 축에 놓이지 않는다.</p><div class="card">')
for name, desc, lanes in BANDS:
    DOC.write('<div class="band"><b>%s</b><em>%s</em><div style="margin-top:5px">%s%s%s</div></div>' % (
        name, desc,
        ''.join(chip(x) for x in lanes.get('web',[])),
        ''.join(chip(x) for x in lanes.get('pop',[])),
        ''.join(chip(x) for x in lanes.get('mob',[]))))
DOC.write('</div>')

DOC.write('''<h2>② 도메인 × 프로그램 <small>단말 편중이 한눈에</small></h2>
<p class="lead">01 자재창고는 <b>모바일</b>(창고 동선), 02 생산실행은 <b>POP</b>(라인 상주), 05·06은 <b>웹</b>(마스터·사무)에 몰린다. 03 품질은 전량 웹 — 판정은 관리웹이라는 정책 4의 결과다.</p>
<div class="card"><table><thead><tr><th>도메인</th><th>관리웹</th><th>POP</th><th>모바일</th><th class="tot">계</th></tr></thead><tbody>''')
DOC.write(''.join(mrows))
DOC.write('<tr><th>합계</th>%s<td class="tot">%d</td></tr></tbody></table></div>' % (mtot, len(ROWS)))

DOC.write('''<h2>③~⑤ 프로그램별 IA — <small>모델이 서로 다르다</small></h2>
<p class="lead">같은 시스템이지만 정보 구조가 셋 다 다르다. <b>관리웹은 메뉴 트리, POP은 태스크 모드(메뉴 아님), 모바일은 스캔 퍼스트 타일</b>이다. 이 차이를 무시하고 하나의 사이트맵으로 그리면 현장에서 안 맞는다.</p>
<h2 style="font-size:15px;margin-top:22px">③ 관리웹 — 메뉴 트리 <small>7개 대분류 · 저장 엔티티가 다르면 다른 화면(규칙 v1.3)</small></h2>
<div class="card">''' + tree_html + '</div>')

DOC.write('<div class="grid3" style="margin-top:16px">'
 '<div><h2 style="font-size:15px;margin-top:0">④ POP — 태스크 모드 <small>메뉴가 아니다</small></h2>'
 '<p class="lead">사번 경량 인증 → W/O 선택 → 작업 모드로 들어간다. 로그인·메뉴 탐색이 없다.</p>'
 '<div class="card">' + pop_html + '</div></div>'
 '<div><h2 style="font-size:15px;margin-top:0">⑤ 모바일 — 스캔 퍼스트 타일 <small>타일 하나 = 작업 단위</small></h2>'
 '<p class="lead">홈에서 타일을 골라 바로 스캔한다. 계정 로그인(M-CO-01) 후 진입.</p>'
 '<div class="card"><div class="tiles">' + tile_html + '</div></div></div></div>')

DOC.write('''<h2>⑥ 최근 변동 <small>v1.2 2계층 매핑 사람 확정 → v1.3 대시보드 정리</small></h2>
<p class="lead">v1.2에서 보류 89건을 사람이 판정해 <b>112 → 113</b>, v1.3에서 대시보드 5건을 삭제해 <b>113 → 108</b>이 됐다. 수보다 <b>구성</b>이 바뀐 것이 핵심이다.</p>
<div class="grid3">
<div><h2 style="font-size:14px;margin-top:0">신설 5 <small>v1.2</small></h2><div class="card">''' + new_html + '</div></div>' +
'<div><h2 style="font-size:14px;margin-top:0">삭제 8 · 이관 1</h2><div class="card">' + gone_html +
'<p style="font-size:12px;color:var(--dim);margin:12px 0 0">범위만 바뀐 화면은 수에 영향이 없다 — v1.2 8건(<code>W-01-01</code> 01-S-C 전 구간 · <code>M-04-01</code> 목록 흡수 · <code>P-02-01</code> 사번 분리 등) + v1.3 <b>집계 뷰 요건 3건</b>(<code>W-03-05</code> 불량률·분포 · <code>W-02-08</code> 생산 실적 · <code>W-01-07</code> 위치별 분포).</p></div></div></div>')

DOC.write('''<h2>⑦ 전체 화면 목록 <small>108건 · 필터</small></h2>
<div class="ctl">
 <button data-f="prog" data-v="all" aria-pressed="true">전체</button>
 <button data-f="prog" data-v="web">관리웹</button>
 <button data-f="prog" data-v="pop">POP</button>
 <button data-f="prog" data-v="mob">모바일</button>
 <span style="width:10px"></span>
 <button data-f="conf" data-v="all" aria-pressed="true">신뢰도 전체</button>
 <button data-f="conf" data-v="확정">확정</button>
 <button data-f="conf" data-v="추정">추정</button>
 <button data-f="conf" data-v="미정">미정</button>
 <input id="q" placeholder="화면명·사용자 검색" autocomplete="off">
 <span id="cnt"></span>
</div>
<div class="card"><table id="tbl"><thead><tr><th>화면ID</th><th>화면명</th><th>유형</th><th>주요 사용자</th><th>도메인</th><th>신뢰도</th></tr></thead><tbody></tbody></table></div>

<p class="foot">CREFLE OMF 팀 (UI/UX) · 내부 대외비 — 외부 공유 금지<br>
이 파일은 외부 asset 참조가 없는 <b>단일 HTML</b>이다(폰트는 시스템 스택, 스크립트·스타일 내장).</p>
</div>
<button id="top">↑ 맨 위</button>
<script>
const R=''' + json.dumps(ROWS, ensure_ascii=False, separators=(',',':')) + ''';
const NEW=new Set(''' + json.dumps(sorted(NEW)) + ''');
const DOM={'01':'01 자재창고','02':'02 생산실행','03':'03 품질','04':'04 제품출하','05':'05 설비·툴','06':'06 기준정보','CO':'공통'};
const PN={web:'관리웹',pop:'POP',mob:'모바일'};
let f={prog:'all',conf:'all',q:''};
const tb=document.querySelector('#tbl tbody'), cnt=document.getElementById('cnt');
function draw(){
 const q=f.q.trim().toLowerCase();
 const rows=R.filter(r=>(f.prog==='all'||r[5]===f.prog)&&(f.conf==='all'||r[4]===f.conf)
   &&(!q||(r[0]+r[1]+r[3]).toLowerCase().includes(q)));
 tb.innerHTML=rows.map(r=>`<tr><td><span class="chip ${r[5]}${NEW.has(r[0])?' new':''}"><b>${r[0]}</b></span></td>`+
  `<td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${DOM[r[6]]} · ${PN[r[5]]}</td>`+
  `<td><span class="pill ${r[4]}">${r[4]}</span></td></tr>`).join('');
 cnt.textContent=rows.length+' / '+R.length+'건';
}
document.querySelectorAll('.ctl button').forEach(b=>b.onclick=()=>{
 const k=b.dataset.f; f[k]=b.dataset.v;
 document.querySelectorAll(`.ctl button[data-f="${k}"]`).forEach(x=>x.setAttribute('aria-pressed',x===b));
 draw();
});
document.getElementById('q').oninput=e=>{f.q=e.target.value;draw()};
document.getElementById('top').onclick=()=>scrollTo({top:0,behavior:'smooth'});
draw();
</script></body></html>''')
DOC.close()
print('생성:', OUT)

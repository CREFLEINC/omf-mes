# -*- coding: utf-8 -*-
"""01·02·03·05 편람 md -> 단일 파일 CREFLE doc HTML. build-04-ia-html.py 계승.

crefle-doc 번들 규약(report 템플릿)을 따르되, 폰트를 base64 로 임베드해
파일 하나로 열리게 한다(04-통합-IA.html·HW 단말기 구성 제안서와 같은 방식·라이선스 동봉).
번들 원천 = design-system-v2-doc dist/crefle-doc (lock 0.1.0, foundation 3a2ee96).

사용법: python3 build-doc-html.py [01|02|03|05|all] [번들경로]
  키 생략 시 all(4건 전부). 번들경로 기본값 = ../uiux/2026-07-25-화면목록-IA/crefle-doc
"""
import base64, html, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT_DEFAULT = os.path.join(HERE, '..', 'uiux', '2026-07-25-화면목록-IA', 'crefle-doc')

# ── 마크다운 변환 (build-04-ia-html.py 계승 + 펜스 코드블록·수평선 지원) ──

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![*\w])\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', t)
    t = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', t)
    return t

NUM = re.compile(r'^[\d,]+(\.\d+)?%?$')

def render(md):
    lines = md.split('\n')
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]

        m = re.match(r'^(#{2,4})\s+(.*)$', ln)
        if m:
            lv = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (lv, inline(m.group(2)), lv))
            i += 1; continue

        if ln.strip() == '```' or ln.startswith('```'):
            lang = ln.strip()[3:].strip()
            buf = []
            i += 1
            while i < n and lines[i].strip() != '```':
                buf.append(lines[i]); i += 1
            i += 1  # 닫는 펜스 소비
            code = html.escape('\n'.join(buf), quote=False)
            cls = ' class="lang-%s"' % lang if lang else ''
            note = '<figcaption>%s 소스 — 이 문서는 렌더러를 내장하지 않아 원문 그대로 싣는다. 시각화는 %s 원본에서 확인.</figcaption>' % (lang, lang) if lang else ''
            out.append('<figure><pre><code%s>%s</code></pre>%s</figure>' % (cls, code, note))
            continue

        if ln.strip() == '---':
            out.append('<hr>')
            i += 1; continue

        if ln.startswith('|') and i + 1 < n and re.match(r'^\|[\s:\-|]+\|$', lines[i+1]):
            head = [c.strip() for c in ln.strip().strip('|').split('|')]
            i += 2
            body = []
            while i < n and lines[i].startswith('|'):
                body.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            wide = len(head) >= 6          # 넓은 표류 — 줄길이 제약 밖으로
            plain = lambda s: re.sub(r'[*`~]', '', s)
            colmax = []
            for ci in range(len(head)):
                vals = [plain(head[ci])] + [plain(r[ci]) for r in body if ci < len(r)]
                colmax.append(max((len(v) for v in vals), default=0))
            narrow = {ci for ci, w in enumerate(colmax) if w <= 8}
            if wide:
                out.append('<figure class="table-wide">')
            out.append('<table>')
            out.append('<thead><tr>' + ''.join(
                '<th%s>%s</th>' % (' class="nw"' if ci in narrow else '', inline(c))
                for ci, c in enumerate(head)) + '</tr></thead>')
            out.append('<tbody>')
            for r in body:
                cells = ['<th%s>%s</th>' % (' class="nw"' if 0 in narrow else '', inline(r[0]))] if r else []
                for ci, c in enumerate(r[1:], start=1):
                    cl = []
                    if NUM.match(plain(c)): cl.append('num')
                    if ci in narrow: cl.append('nw')
                    cells.append('<td%s>%s</td>' % (' class="%s"' % ' '.join(cl) if cl else '', inline(c)))
                out.append('<tr>' + ''.join(cells) + '</tr>')
            out.append('</tbody></table>')
            if wide:
                out.append('</figure>')
            continue

        if ln.startswith('>'):
            buf = []
            while i < n and (lines[i].startswith('>') or (buf and lines[i].strip() == '' and i+1 < n and lines[i+1].startswith('>'))):
                buf.append(re.sub(r'^>\s?', '', lines[i])); i += 1
            body = '\n'.join(buf).strip()
            cls = 'callout callout-warning' if re.match(r'^[⛔⚠]|^\*\*[⛔⚠]', body) else 'callout'
            out.append('<div class="%s">%s</div>' % (cls, render(body)))
            continue

        if re.match(r'^\d+\.\s+', ln):
            items = []
            while i < n and (re.match(r'^\d+\.\s+', lines[i]) or (lines[i].strip() and lines[i].startswith('   ') and items)):
                mm = re.match(r'^\d+\.\s+(.*)$', lines[i])
                if mm:
                    items.append(mm.group(1))
                else:
                    items[-1] += ' ' + lines[i].strip()
                i += 1
            out.append('<ol>' + ''.join('<li>%s</li>' % inline(t) for t in items) + '</ol>')
            continue

        if re.match(r'^(\s*)[-*]\s+', ln):
            items = []
            while i < n and (re.match(r'^(\s*)[-*]\s+', lines[i]) or (lines[i].strip() and lines[i].startswith('  ') and items)):
                mm = re.match(r'^(\s*)[-*]\s+(.*)$', lines[i])
                if mm:
                    items.append((len(mm.group(1)) // 2, mm.group(2)))
                else:
                    items[-1] = (items[-1][0], items[-1][1] + ' ' + lines[i].strip())
                i += 1
            out.append(build_list(items))
            continue

        if ln.strip() == '':
            i += 1; continue

        buf = [ln]; i += 1
        while i < n and lines[i].strip() and not re.match(r'^(#{2,4}\s|```|---$|\||>|\s*[-*]\s|\d+\.\s)', lines[i]):
            buf.append(lines[i]); i += 1
        out.append('<p>%s</p>' % inline(' '.join(buf)))
    return '\n'.join(out)

def build_list(items):
    html_out, stack = [], []
    for lv, txt in items:
        while len(stack) > lv + 1:
            html_out.append('</ul></li>'); stack.pop()
        if len(stack) == lv + 1:
            html_out.append('</li>')
        else:
            html_out.append('<ul>')
            stack.append(lv)
        html_out.append('<li>%s' % inline(txt))
    html_out.append('</li>')
    while len(stack) > 1:
        html_out.append('</ul></li>'); stack.pop()
    html_out.append('</ul>')
    return ''.join(html_out)

# ── 번들 인라인 (단일 파일화) ──

def css_with_fonts(kit):
    css = io.open(os.path.join(kit, 'crefle-doc.css'), encoding='utf-8').read()
    def repl(m):
        rel = m.group(1)
        p = os.path.join(kit, rel)
        b64 = base64.b64encode(open(p, 'rb').read()).decode('ascii')
        return "url(data:font/woff2;base64,%s)" % b64
    out = re.sub(r"url\('\./(fonts/[^']+\.woff2)'\)", repl, css)
    assert "url('./fonts/" not in out, '폰트 참조 잔존'
    return out

def licenses(kit):
    parts = []
    for f in ('LICENSE-MaterialSymbols.txt', 'LICENSE-SpoqaHanSansNeo.txt', 'LICENSE-JetBrainsMono.txt'):
        body = io.open(os.path.join(kit, 'fonts', f), encoding='utf-8', errors='replace').read()
        body = body.replace('--', '\u2010\u2010')  # HTML 주석 안전화
        parts.append('=' * 72 + '\n' + f + '\n' + '=' * 72 + '\n\n' + body)
    return '\n\n'.join(parts)

# ── 문서별 설정 ──

CONFIG = {
    '00': dict(
        src='00-용어사전.md', dst='00-용어사전.html',
        title='OMF-MES 용어 사전',
        lede='이 프로젝트가 만들어 쓰는 말의 뜻을 모은 것. 편람 01~06과 uiux/ 문서를 읽다 막히는 말이 있으면 여기를 본다. 문서를 고치는 대신 사전을 둔다 — 원문의 맥락이 보존된다.',
        kpi=[('27', '항목<br>5군 분류'),
             ('5', '분류<br>화면·API·DS·문서·공통'),
             ('96', '「미착지」 출현<br>원문 그대로 보존')],
        version_note='v1.0 (초판 — 「미착지」가 읽히지 않는다는 지적에서 출발)',
    ),
    '01': dict(
        src='01-요구사항명세서.md', dst='01-요구사항명세서.html',
        title='OMF-MES 요구사항명세서 (통합 정리본)',
        lede='요구 원문 47건(부품 36+OA 11, 2026-07-01 고객 서명)의 요지·해석·확정/재정의·반영 위치·잔여 미결을 한 곳에 모은 추적성 편람. 원본과 다르면 원본이 이긴다.',
        kpi=[('47', 'REQ 전건<br>부품 36 · OA 11'),
             ('16', '정합주(원본 스테일 정정)'),
             ('2', '재정의 반영<br>PR-0001 · PR-0007')],
        version_note='v1.0 (초판 — deliverables/01-요구사항명세서.md 와 동일 내용의 HTML 판)',
    ),
    '02': dict(
        src='02-SW설계사양서.md', dst='02-SW설계사양서.html',
        title='OMF-MES SW설계사양서 (통합 정리본)',
        lede='아키텍처·인증·데이터·ERP 연계와 도메인별 설계 규칙 전건, 통합 결정 대장·미결 총괄을 한 곳에 모은 개발 착수용 편람. 원본과 어긋나면 원본이 우선한다.',
        kpi=[('338', '도메인 설계 규칙 전건 (§6)'),
             ('142', '통합 결정 대장 행 (§7)'),
             ('107', '미결 총괄 행 (§8)')],
        version_note='v1.0 (초판 — deliverables/02-SW설계사양서.md 와 동일 내용의 HTML 판)',
    ),
    '03': dict(
        src='03-HW구성안.md', dst='03-HW구성안.html',
        title='OMF-MES H/W 구성안 (제안 미확정분)',
        lede='단말·스테이션 표준 모듈·조합과 제안 구성·금액을 정리한 편람. ⛔ 고객사가 단말기 종류·설치 위치·수량을 정리해 전달하기로 함(리더 결정 2026-07-30) — 회신 수령 전 개별 항목 수정 보류, 확정 견적은 회신 후 재산정.',
        kpi=[('122,824,000', '제안 총액(원)'),
             ('15', '스펙↔제안서 불일치 전건'),
             ('23', '미확정 총괄(제안서 7·스펙 14·재확인 2)')],
        version_note='v1.0 (초판 — deliverables/03-HW구성안.md 와 동일 내용의 HTML 판, 제안 미확정 스냅샷)',
    ),
    '05': dict(
        src='05-사용자-프로세스-태스크플로우.md', dst='05-사용자-프로세스-태스크플로우.html',
        title='OMF-MES 사용자 프로세스·태스크 플로우 (통합 정리본)',
        lede='「누가·어느 단말·어느 화면에서·무엇을 하는가」를 도메인 01~06 단계 단위로 모은 개발 열람용 편람. 원본과 어긋나면 원본이 우선한다.',
        kpi=[('61', '단계 전건<br>사이드 31 · 예외 63'),
             ('43', '역할별 태스크 인덱스 (§9)'),
             ('6', '도메인 커버 (01~06, §3~8)')],
        version_note='v1.0 (초판 — deliverables/05-사용자-프로세스-태스크플로우.md 와 동일 내용의 HTML 판)',
    ),
    '06': dict(
        src='06-API-요구서.md', dst='06-API-요구서.html',
        title='OMF-MES 기준정보 도메인 API 요구서 (통합 정리본)',
        lede='화면 상세 스펙 10장이 API 에 무엇을 요구하는지 매핑하고, 그 API 로 화면을 실제로 그릴 수 있는지 판정한 편람. 필드 정의의 정본은 물리 모델이고 계약은 `openapi/mdm-기준정보.json` — 이 문서는 왜·어디서만 담는다. 원본과 어긋나면 물리 모델·OpenAPI가 이긴다.',
        kpi=[('71', '화면→API 매핑 액션<br>대응 54 · 없음+이유 17'),
             ('50', '적합성 판정 셀<br>✅ 36 · ⚠ 14 · ❌ 0'),
             ('16', '미착지 건<br>전건 발행 · 미발행 0')],
        version_note='v0.2 (deliverables/06-API-요구서.md 와 동일 내용의 HTML 판 — 사용자 확정 4건 반영판)',
    ),
}

# ── 조립 ──

def build(key, kit):
    cfg = CONFIG[key]
    src = os.path.join(HERE, cfg['src'])
    dst = os.path.join(HERE, cfg['dst'])
    md = io.open(src, encoding='utf-8').read()
    body = md.split('\n', 1)[1].lstrip('\n')        # H1 제거(선행 빈 줄까지)

    meta, rest, meta_done = [], [], False
    for ln in body.split('\n'):
        if not meta_done and ln.startswith('> '):
            meta.append(re.sub(r'^>\s?', '', ln))
        elif not meta_done and ln.strip() == '' and not meta:
            continue                                 # 헤더 앞 빈 줄
        elif not meta_done and ln.strip() == '' and meta:
            meta_done = True                         # 메타 블록 종료 — 이후 인용문은 본문 콜아웃으로
        else:
            meta_done = True
            rest.append(ln)
    overview = '\n'.join('<p>%s</p>' % inline(m) for m in meta)
    doc = render('\n'.join(rest))

    kpi_html = ''.join('<div><span class="big">%s</span><span class="lbl">%s</span></div>' % (a, b) for a, b in cfg['kpi'])

    html_out = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>%s</title>

<!--
  이 문서에는 아래 폰트가 base64 로 임베드되어 있습니다. 각 라이선스 전문을 함께 싣습니다.
    · MaterialSymbols
    · SpoqaHanSansNeo
    · JetBrainsMono

%s
-->

<style>
%s
</style>
<style>
  :root { --doc-running-title: '%s'; }

  /* 이 문서 1회용 — 넓은 표(6열 이상)를 본문 줄길이(--doc-measure 78ch) 밖으로 넓힌다.
     crefle-doc.css 가 .doc > table 에 max-width:none 을 주지만, 부모 .doc 자체가 measure 로
     묶여 있어 다열 표에서는 열이 한 글자씩 세로로 깨진다. 색은 쓰지 않고 폭·정렬만 조정한다.
     같은 필요가 세 문서 이상에서 반복돼 DS 컴포넌트 후보다(스킬 「없는 컴포넌트가 필요하면」). */
  .doc > figure.table-wide {
    width: min(96vw, 1560px);
    margin-inline: calc((100%% - min(96vw, 1560px)) / 2);
    overflow-x: auto;
  }
  .doc > figure.table-wide > table { width: 100%%; }
  .doc > figure.table-wide code { white-space: nowrap; }
  .doc table .nw { white-space: nowrap; }
  .doc > figure.table-wide table { word-break: keep-all; }

  @media print {
    .doc > figure.table-wide { width: 100%%; margin-inline: 0; overflow-x: visible; }
  }
</style>
</head>
<body class="doc">

<header class="doc-cover">
  <p class="eyebrow">CREFLE · OMF-MES · 통합 편람</p>
  <h1>%s</h1>
  <p class="lede">%s</p>
  <table>
    <caption>문서 정보</caption>
    <tbody>
      <tr><th>작성 주체</th><td>CREFLE OMF 팀</td></tr>
      <tr><th>작성일</th><td>2026-07-30</td></tr>
      <tr><th>버전</th><td>%s</td></tr>
      <tr><th>대상</th><td>CREFLE OMF 팀 내부 (내부 대외비)</td></tr>
      <tr><th>정본 관계</th><td>원본(docs/·uiux/)이 정본 — 편람은 추종, 어긋나면 원본 우선</td></tr>
    </tbody>
  </table>
</header>

<h2>문서 개요</h2>
%s
<div class="kpi">%s</div>

%s

</body>
</html>
""" % (cfg['title'], licenses(kit), css_with_fonts(kit), cfg['title'], cfg['title'],
       inline(cfg['lede']), cfg['version_note'], overview, kpi_html, doc)

    io.open(dst, 'w', encoding='utf-8').write(html_out)
    print('생성:', dst, '(%d bytes)' % os.path.getsize(dst))

def main():
    argv = sys.argv[1:]
    sel = argv[0] if argv else 'all'
    kit = argv[1] if len(argv) > 1 else KIT_DEFAULT
    keys = list(CONFIG.keys()) if sel == 'all' else [sel]
    for k in keys:
        build(k, kit)

if __name__ == '__main__':
    main()

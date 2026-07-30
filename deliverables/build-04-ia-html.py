# -*- coding: utf-8 -*-
"""04-통합-IA.md -> 단일 파일 CREFLE doc HTML.

crefle-doc 번들 규약(report 템플릿)을 따르되, 폰트를 base64 로 임베드해
파일 하나로 열리게 한다(HW 단말기 구성 제안서와 같은 방식 · 라이선스 동봉).
번들 원천 = design-system-v2-doc dist/crefle-doc (lock 0.1.0, foundation 3a2ee96).
사용법: python3 build-04-ia-html.py [번들경로]
  번들경로 기본값 = ../uiux/2026-07-25-화면목록-IA/crefle-doc (저장소 내 동일 lock 사본)
"""
import base64, html, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '04-통합-IA.md')
DST = os.path.join(HERE, '04-통합-IA.html')
KIT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, '..', 'uiux', '2026-07-25-화면목록-IA', 'crefle-doc')

# ── 마크다운 변환 (uiux/2026-07-25-화면목록-IA/build-정식본.py 계승 + 순서 목록 지원) ──

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

        if ln.startswith('|') and i + 1 < n and re.match(r'^\|[\s:\-|]+\|$', lines[i+1]):
            head = [c.strip() for c in ln.strip().strip('|').split('|')]
            i += 2
            body = []
            while i < n and lines[i].startswith('|'):
                body.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            wide = len(head) >= 6          # 화면 인벤토리 7열류 — 줄길이 제약 밖으로
            # 짧은 열(유형·신뢰도류)은 자동 레이아웃이 한 글자씩 접어버린다 — 내용 길이로 판정해 nowrap
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

        # 순서 목록 (평탄)
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
        while i < n and lines[i].strip() and not re.match(r'^(#{2,4}\s|\||>|\s*[-*]\s|\d+\.\s)', lines[i]):
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

# ── 조립 ──

def main():
    md = io.open(SRC, encoding='utf-8').read()
    body = md.split('\n', 1)[1].lstrip('\n')        # H1 제거 (선행 빈 줄까지)
    meta, rest = [], []
    for ln in body.split('\n'):
        if ln.startswith('> ') and not rest:
            meta.append(re.sub(r'^>\s?', '', ln))
        elif ln.strip() == '' and not rest and meta:
            continue
        else:
            rest.append(ln)
    overview = '\n'.join('<p>%s</p>' % inline(m) for m in meta)
    doc = render('\n'.join(rest))

    kpi = ''.join('<div><span class="big">%s</span><span class="lbl">%s</span></div>' % (a, b) for a, b in [
        ('109', '화면 전건<br>관리웹 68 · POP 22 · 모바일 19'),
        ('82', '신뢰도 확정<br>추정 25 · 미정 2'),
        ('3', 'IA 모델<br>메뉴트리 · 태스크모드 · 스캔타일'),
    ])

    html_out = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>OMF-MES 통합 IA (정보 구조)</title>

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
  :root { --doc-running-title: 'OMF-MES 통합 IA'; }

  /* 이 문서 1회용 — 화면 인벤토리 7열 표(§3~§5)를 본문 줄길이(--doc-measure 78ch) 밖으로 넓힌다.
     crefle-doc.css 가 「표·차트·코드는 줄길이 제약을 벗어난다 — 데이터는 넓어야 읽힌다」로
     .doc > table 에 max-width:none 을 주지만, 부모 .doc 자체가 measure 로 묶여 있어
     7열에서는 열이 한 글자씩 세로로 깨진다. 색은 쓰지 않고 폭·정렬만 조정한다.
     같은 필요가 세 문서에서 반복되면 DS 컴포넌트 후보다(스킬 「없는 컴포넌트가 필요하면」). */
  .doc > figure.table-wide {
    width: min(96vw, 1560px);
    margin-inline: calc((100%% - min(96vw, 1560px)) / 2);
    overflow-x: auto;
  }
  .doc > figure.table-wide > table { width: 100%%; }
  .doc > figure.table-wide code { white-space: nowrap; }   /* 화면 ID 가 중간에서 끊기지 않게 */
  .doc table .nw { white-space: nowrap; }                  /* 짧은 열(유형·신뢰도류) 세로 깨짐 방지 */
  .doc > figure.table-wide table { word-break: keep-all; } /* 한국어는 어절 단위로만 끊는다 */

  @media print {
    .doc > figure.table-wide { width: 100%%; margin-inline: 0; overflow-x: visible; }
  }
</style>
</head>
<body class="doc">

<header class="doc-cover">
  <p class="eyebrow">CREFLE · OMF-MES · 통합 편람</p>
  <h1>OMF-MES 통합 IA (정보 구조)</h1>
  <p class="lede">관리웹·POP·모바일 3종의 화면 인벤토리 109건 전건과 프로그램별 정보 구조(IA), 배지 배정·미결·상세 스펙 이월 요건을 한 문서로 모은 개발 열람용 편람. 화면 정본은 uiux/2026-07-25-화면목록-IA/screen-inventory-ia.md v1.3.</p>
  <table>
    <caption>문서 정보</caption>
    <tbody>
      <tr><th>작성 주체</th><td>CREFLE OMF 팀</td></tr>
      <tr><th>작성일</th><td>2026-07-30</td></tr>
      <tr><th>버전</th><td>v1.0 (초판 — deliverables/04-통합-IA.md 와 동일 내용의 HTML 판)</td></tr>
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
""" % (licenses(KIT), css_with_fonts(KIT), overview, kpi, doc)

    io.open(DST, 'w', encoding='utf-8').write(html_out)
    print('생성:', DST, '(%d bytes)' % os.path.getsize(DST))

if __name__ == '__main__':
    main()

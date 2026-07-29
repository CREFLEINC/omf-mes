# -*- coding: utf-8 -*-
"""screen-inventory-ia.md -> CREFLE doc HTML (crefle-doc 번들 규약)."""
import io, re, sys, html

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

        # heading
        m = re.match(r'^(#{2,4})\s+(.*)$', ln)
        if m:
            lv = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (lv, inline(m.group(2)), lv))
            i += 1; continue

        # table
        if ln.startswith('|') and i + 1 < n and re.match(r'^\|[\s:\-|]+\|$', lines[i+1]):
            head = [c.strip() for c in ln.strip().strip('|').split('|')]
            i += 2
            body = []
            while i < n and lines[i].startswith('|'):
                body.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            out.append('<table>')
            out.append('<thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in head) + '</tr></thead>')
            out.append('<tbody>')
            for r in body:
                cells = ['<th>%s</th>' % inline(r[0])] if r else []
                for c in r[1:]:
                    cls = ' class="num"' if NUM.match(re.sub(r'[*`]', '', c)) else ''
                    cells.append('<td%s>%s</td>' % (cls, inline(c)))
                out.append('<tr>' + ''.join(cells) + '</tr>')
            out.append('</tbody></table>')
            continue

        # blockquote block -> callout
        if ln.startswith('>'):
            buf = []
            while i < n and (lines[i].startswith('>') or (buf and lines[i].strip() == '' and i+1 < n and lines[i+1].startswith('>'))):
                buf.append(re.sub(r'^>\s?', '', lines[i])); i += 1
            inner = render('\n'.join(buf).strip())
            out.append('<div class="callout">%s</div>' % inner)
            continue

        # list block (nested by 2-space indent)
        if re.match(r'^(\s*)[-*]\s+', ln):
            items = []
            while i < n and (re.match(r'^(\s*)[-*]\s+', lines[i]) or (lines[i].strip() and lines[i].startswith('  ') and items)):
                mm = re.match(r'^(\s*)[-*]\s+(.*)$', lines[i])
                if mm:
                    items.append((len(mm.group(1)) // 2, mm.group(2)))
                else:                                   # 이어지는 줄
                    items[-1] = (items[-1][0], items[-1][1] + ' ' + lines[i].strip())
                i += 1
            out.append(build_list(items))
            continue

        if ln.strip() == '':
            i += 1; continue

        # paragraph
        buf = [ln]; i += 1
        while i < n and lines[i].strip() and not re.match(r'^(#{2,4}\s|\||>|\s*[-*]\s)', lines[i]):
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
            html_out.append('<ul>' if not stack else '<ul>')
            stack.append(lv)
        html_out.append('<li>%s' % inline(txt))
    html_out.append('</li>')
    while len(stack) > 1:
        html_out.append('</ul></li>'); stack.pop()
    html_out.append('</ul>')
    return ''.join(html_out)

def main(src, dst, title, running, lede, kpi):
    md = io.open(src, encoding='utf-8').read()
    body = md.split('\n', 1)[1]            # H1 제거
    # 상단 인용(> 로 시작하는 메타 블록)을 문서 개요로 승격
    meta = []
    rest = []
    for ln in body.split('\n'):
        if ln.startswith('> ') and not rest:
            meta.append(re.sub(r'^>\s?', '', ln))
        elif ln.strip() == '' and not rest and meta:
            continue
        else:
            rest.append(ln)
    overview = '\n'.join('<p>%s</p>' % inline(m) for m in meta)
    doc = render('\n'.join(rest))
    k = ''.join('<div><span class="big">%s</span><span class="lbl">%s</span></div>' % (a, b) for a, b in kpi)
    io.open(dst, 'w', encoding='utf-8').write("""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="./crefle-doc/crefle-doc.css">
<style>
  :root { --doc-running-title: '%s'; }
</style>
</head>
<body class="doc">

<header class="doc-cover">
  <p class="eyebrow">CREFLE · OMF UI/UX · 정보 구조(IA)</p>
  <h1>%s</h1>
  <p class="lede">%s</p>
  <table>
    <caption>문서 정보</caption>
    <tbody>
      <tr><th>작성 주체</th><td>CREFLE OMF 팀 (UI/UX)</td></tr>
      <tr><th>작성일</th><td>2026-07-25 (v1.3 개정 2026-07-29)</td></tr>
      <tr><th>버전</th><td>v1.3</td></tr>
      <tr><th>대상</th><td>CREFLE OMF 팀 내부 (내부 대외비)</td></tr>
    </tbody>
  </table>
</header>

<h2>문서 개요</h2>
%s
<div class="kpi">%s</div>

%s

<script src="./crefle-doc/crefle-chart.js"></script>
</body>
</html>
""" % (title, running, title, lede, overview, k, doc))
    print('생성:', dst)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2],
         '프로그램별 화면 목록 · IA (정보 구조)',
         '프로그램별 화면 목록 · IA',
         '관리웹·POP·모바일 3종의 화면 인벤토리 109건과 프로그램별 정보 구조(IA). 대시보드 5건 삭제·집계 뷰 요건 3건 명시를 반영한 v1.3.',
         [('109', '화면<br>관리웹68·POP22·모바일19'),
          ('3', '프로그램<br>(IA 모델 3종)'),
          ('82', '확정<br>(추정25·미정2)'),
          ('73', '화면 그룹<br>도식 미대응 0')])

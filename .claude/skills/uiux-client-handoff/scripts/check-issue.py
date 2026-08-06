# -*- coding: utf-8 -*-
"""착수 가능 통지 초안을 발행 전에 검사한다.

왜 필요한가
  omf-mes-client 는 **공개 저장소**다. 이슈의 제목·본문·첨부·라벨·수정 이력이
  전부 함께 공개되고, 지워도 인덱싱된 사본과 포크는 회수되지 않는다.

  2026-08-04 에 DS 저장소에서 **발행 후에** 검사하다 제품 용어 2건을 흘렸다.
  즉시 수정했으나 수정 이력에는 원문이 남았다. 그래서 순서를 못박았다 —
  본문 작성 → 검사 → 발행.

무엇을 보나
  ① 구조 — 폼 6항목이 다 있는가 · 4번 처리 방법이 3종 중 하나인가 · 미기입 자리표시가 남았는가
  ② 공개 안전 — 이미지 · 조항 요약 · 확정 기록 마커 · 실 운영값 · 인프라 · 금액

  ⛔ 위반은 종료 코드 1. ⚠ 확인은 사람이 판단할 것이라 막지 않는다.

사용법
  python3 check-issue.py <초안.md>                  # 착수 가능 통지
  python3 check-issue.py <초안.md> --change-notice  # ⛔/⚠ 변경 통지 (구조 검증 생략)
  python3 check-issue.py <초안.md> --title "..."    # 통과 시 gh 명령까지 출력
"""
import io
import os
import re
import sys

REPO = 'CREFLEINC/omf-mes-client'
LABELS = 'uiux→client,ready'

REQUIRED_SECTIONS = [
    '1. 화면 ID · 이름',
    '1-2. 리소스 패턴',
    '2. 근거',
    '2-2. 확인 시점',
    '3. 확정된 것',
    '4. 미결 항목',
    '5. 선행·순서',
    '6. 특별히 조심할 것',
]

PATTERNS = [
    '마스터 형',
    '버전 마스터 형',
    '조회 형',
    '입력 형',
]

# 폼이 정한 세 가지. 이 밖의 표현을 쓰면 프론트가 무엇을 하라는 것인지 모른다.
HANDLINGS = [
    '만들지 않는다',
    '자리표시 상수',
    '비활성',
]

# ⛔ 위반 — (이름, 정규식, 왜)
BLOCKING = [
    ('이미지',
     re.compile(r'!\[[^\]]*\]\(|<img\s|user-attachments/assets|user-images\.githubusercontent'),
     '와이어프레임·화면 캡처·도식은 금지다. 화면 ID 와 말로 설명한다'),

    ('공유계약 조항 요약',
     re.compile(r'(?:공유계약\s*)?\b[A-L]-\d+\s*\('),
     '괄호 안 요약이 조항 본문이다. 번호만 남긴다 — 「공유계약 B-1 을 따른다」'),

    ('확정 기록 마커',
     re.compile(r'✓\s*확정|✓\s*설계확정|✅\s*REQ-|✓확정 QA|결정\s*\d+\s*[「(]'),
     '내부 문서 체계의 이름이라 프론트에게 도움이 안 된다. 일반 표현이나 omf-mes#번호로'),

    ('실 사번 의심',
     re.compile(r'\b9\d{5}\b'),
     '실 사번 형식(6자리·90****)이다. 합성값을 쓴다'),

    ('실 LOT 번호 의심',
     re.compile(r'\b[A-Z]{1,3}-?20\d{6}-\d{3,4}\b'),
     '실 LOT 번호 형식이다. 합성값을 쓴다'),

    ('인프라 정보',
     re.compile(r'\b\d{1,3}(?:\.\d{1,3}){3}\b|://[^\s/]*:[^\s/]*@|:(?:5432|3306|6379|27017|8080|1521)\b'),
     'IP·포트·접속 문자열은 금지다'),

    ('금액·단가·납기',
     re.compile(r'\d[\d,]*\s*원\b|₩\s*\d|\b(?:USD|KRW)\s*\d|단가|견적가|계약\s*금액|납기일'),
     '계약·견적 정보는 금지다'),

    ('스펙 본문 인용 의심',
     re.compile(r'^>\s*\S.{40,}', re.MULTILINE),
     '블록 인용으로 긴 문장이 들어왔다. 스펙 본문 복사인지 확인하고 요약이 아니라 포인터로 바꾼다'),
]

# ⚠ 확인 — 자동으로 막지 않는다. 사람이 판단한다.
ADVISORY = [
    ('요구사항 번호',
     re.compile(r'REQ-(?:PR|OA)-\d{4}'),
     '번호만이면 포인터라 허용. 제목을 붙이면 내용이 된다 — 뒤에 설명이 붙었는지 본다'),

    ('물리 모델 컬럼 표기',
     re.compile(r'\b(?:mdm|app|trace|quality|production|logistics|inventory|planning|audit|integration)\.\w+\.\w+'),
     '계약 정본에 이미 있는 필드면 허용(공개된 api.d.ts 에 들어 있다). 계약에 없는 내부 컬럼이면 화면 용어로 바꾼다'),

    ('「」 안 긴 문장',
     re.compile(r'「[^」]{40,}」'),
     '문서 본문 발췌인지 확인한다. 화면에 실제로 표시할 문구면 허용'),

    ('docs/research 경로',
     re.compile(r'docs/research/'),
     '경로는 포인터라 허용이나, research 는 원본 자료라 파일명 자체가 내용을 드러낼 수 있다'),
]

PLACEHOLDER = re.compile(r'<[가-힣][^>]*>|W-00-00|omf-mes#00|YYYY-MM-DD|v0\.0|<해시>')


def sections(text):
    """### 로 시작하는 절을 {제목: 본문} 으로."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r'^###\s+(.+?)\s*$', line)
        if m:
            if cur is not None:
                out[cur] = '\n'.join(buf).strip()
            cur, buf = m.group(1), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = '\n'.join(buf).strip()
    return out


def check_structure(text, secs):
    errs, warns = [], []

    found = list(secs)
    for want in REQUIRED_SECTIONS:
        if not any(h.startswith(want) for h in found):
            errs.append(('구조', '「%s」 절이 없다' % want,
                         '폼이 렌더하는 제목 그대로 써야 웹 폼 이슈와 같은 모양이 된다'))

    def body(prefix):
        for h, b in secs.items():
            if h.startswith(prefix):
                return b
        return ''

    pat = body('1-2.')
    if pat and not any(pat.startswith(p) for p in PATTERNS):
        errs.append(('리소스 패턴', pat.splitlines()[0][:60] if pat else '(비어 있음)',
                     '폼 드롭다운 4개 중 하나를 그대로 써야 한다: ' + ' / '.join(PATTERNS)))

    when = body('2-2.')
    if when and not re.match(r'^\d{4}-\d{2}-\d{2}\s*$', when.strip()):
        errs.append(('확인 시점', when.strip()[:40], '날짜 하나만 적는다 (YYYY-MM-DD)'))

    open_items = body('4.')
    if open_items and open_items.strip() != '없음':
        rows = [r for r in open_items.splitlines()
                if r.strip().startswith('|') and '---' not in r]
        rows = rows[1:] if rows else []          # 헤더 제외
        if not rows:
            errs.append(('미결', '표도 「없음」도 없다',
                         '이 칸이 비면 프론트가 미결을 혼자 판단한다. 없으면 「없음」이라 적는다'))
        for r in rows:
            cells = [c.strip() for c in r.strip().strip('|').split('|')]
            how = cells[2] if len(cells) > 2 else ''
            if not any(h in how for h in HANDLINGS):
                errs.append(('미결 처리 방법', how[:50] or '(비어 있음)',
                             '반드시 셋 중 하나: ' + ' / '.join(HANDLINGS)))
            if len(cells) > 3 and not cells[3].strip():
                warns.append(('추적 번호 없음', cells[0][:30],
                              'omf-mes#번호를 적으면 나중에 무엇이 풀렸는지 따라갈 수 있다'))

    settled = body('3.')
    unchecked = [l for l in settled.splitlines() if l.strip().startswith('- [ ]')]
    if unchecked and open_items.strip() == '없음':
        errs.append(('3번 ↔ 4번 모순', '체크 안 한 항목 %d 개' % len(unchecked),
                     '체크하지 않은 것은 곧 미결이다. 4번에 처리 방법을 적는다'))
    elif unchecked:
        rows = [r for r in open_items.splitlines()
                if r.strip().startswith('|') and '---' not in r][1:]
        if len(rows) < len(unchecked):
            warns.append(('3번 ↔ 4번 개수', '체크 안 함 %d · 미결 행 %d'
                          % (len(unchecked), len(rows)),
                          '체크하지 않은 항목이 4번에 다 들어갔는지 본다. '
                          '빠지면 프론트가 그것을 혼자 판단한다'))

    return errs, warns


def scan(text, rules):
    hits = []
    for name, rx, fix in rules:
        for m in rx.finditer(text):
            s = max(0, m.start() - 30)
            snippet = text[s:m.end() + 30].replace('\n', ' ')
            hits.append((name, snippet, fix))
    return hits


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    change_notice = '--change-notice' in sys.argv
    title = None
    if '--title' in sys.argv:
        i = sys.argv.index('--title')
        if i + 1 < len(sys.argv):
            title = sys.argv[i + 1]

    text = io.open(path, encoding='utf-8').read()
    secs = sections(text)

    errs, warns = ([], [])
    if not change_notice:
        errs, warns = check_structure(text, secs)

    left = PLACEHOLDER.findall(text)
    if left:
        errs.append(('미기입 자리표시', ' · '.join(sorted(set(left))[:6]),
                     '초안 자리표시가 남아 있다. 전부 채운다'))

    errs += scan(text, BLOCKING)
    warns += scan(text, ADVISORY)

    kind = '변경 통지' if change_notice else '착수 가능 통지'
    print('%s 검사 — %s' % (kind, os.path.basename(path)))
    print('─' * 66)

    if warns:
        print('\n⚠ 확인 %d 건 — 막지 않는다. 사람이 판단한다.\n' % len(warns))
        for name, snippet, fix in warns:
            print('  [%s]' % name)
            print('    …%s…' % snippet[:110])
            print('    → %s' % fix)

    if errs:
        print('\n⛔ 위반 %d 건\n' % len(errs))
        for name, snippet, fix in errs:
            print('  [%s]' % name)
            print('    …%s…' % snippet[:110])
            print('    → %s' % fix)
        print('\n공개 저장소입니다. 고치고 다시 검사하세요.')
        return 1

    print('\n✅ 발행해도 되는 상태입니다.')

    if title:
        print('\n─ 발행 명령 ' + '─' * 52)
        print('gh issue create --repo %s \\' % REPO)
        print('  --title %s \\' % _q(title))
        print('  --body-file %s \\' % _q(path))
        print('  --label %s' % _q(LABELS))
        print('\n⚠ --label 을 빼지 마세요 — CLI 는 폼을 거치지 않아 라벨이 자동으로 붙지 않습니다.')
    else:
        print('\n(--title "…" 을 주면 gh 명령까지 만들어 줍니다)')
    return 0


def _q(s):
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == '__main__':
    sys.exit(main())

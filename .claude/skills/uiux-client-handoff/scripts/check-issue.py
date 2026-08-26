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

  ③ 회신 규약 — 첫 줄이 「## 개발팀 전달사항」으로 시작하는가 (--reply 전용)

  ⚠ --reply 는 ①과 중복 검사를 «끄고» ②③을 본다. 회신은 새 이슈가 아니라 «요청 이슈의
     코멘트»라 폼 6항목도, 「같은 화면의 착수 이슈가 이미 있다」는 중복 판정도 성립하지
     않는다(답하는 대상이 바로 그 이슈다).

     2026-08-26 omf-mes-client#442 회신에서 드러났다 — 폼 검사로 돌려 ⛔ 9건이 떴는데
     전부 [구조]·[중복 발행]이었고 공개 안전 위반은 0건이었다. 모드가 없어 사람이
     「막지 않아도 되는 위반」을 매번 손으로 갈라야 했다.

  ⚠ --reply --private 는 ②를 «끄고» ③만 본다. 검토 요청의 다수는 비공개 omf-mes 로 오고,
     거기서는 단가·조항 요약·내부 주소가 막을 이유가 없는데 막힌다. 반대로 ③은 «비공개
     회신에도» 필요하다 — 머리 표기 위반 실측 2건(#232·#222)이 둘 다 비공개 회신이었다.
     그래서 ②와 ③을 한 모드에 묶지 않고 갈랐다.

     기본은 ② 켜짐이다. 끄는 것을 잊으면 과하게 막힐 뿐이지만, 켜는 것을 잊으면 흘러나간다.
     --private 는 --reply 와 함께만 쓴다(착수·변경 통지는 언제나 공개 저장소로 나간다).

  ⛔ 위반은 종료 코드 1. ⚠ 확인은 사람이 판단할 것이라 막지 않는다.

  ④ 중복·금지 화면 — 같은 화면에 이미 착수 이슈가 있는가 · 발행 금지 화면인가

     ⚠ 이것을 사람의 기억에 맡기지 않는다. 닫힌 이슈는 기본 목록에 안 보이고,
     차수가 쌓이면 「이 화면 넘겼던가」를 기억으로 답하게 된다. 발행은 되돌릴 수
     없으므로(공개 저장소) 검사기가 매번 조회한다.

사용법
  python3 check-issue.py <초안.md>                  # 착수 가능 통지
  python3 check-issue.py <초안.md> --change-notice  # ⛔/⚠ 변경 통지 (구조 검증 생략)
  python3 check-issue.py <초안.md> --title "..."    # 통과 시 gh 명령까지 출력
  python3 check-issue.py <초안.md> --team T4        # 통과 시 gh 명령의 라벨에 Agent : T4 를 병기
  python3 check-issue.py --status                   # 발행 현황만 조회
  python3 check-issue.py <초안.md> --no-remote      # 원격 조회 생략 (오프라인)

팀 라벨 병기 (team-issue-protocol §2)
  omf-mes-client 는 uiux→client·ready 두 라벨만 써 왔지만, multi-agent-team-workflow-v2.md
  체계에서는 어느 개발팀이 담당인지 Agent : T{n} 라벨로도 식별한다. --team 을 주면 그 값을
  --label 병기에 반영하고, 주지 않으면 같은 화면·같은 도메인의 기존 이슈에서 이미 쓰인
  Agent : T{n} 라벨을 조회해 「이런 값이 보인다」로만 제안한다(자동 부착하지 않는다 — 팀
  배정은 design-work-assignment 의 승인을 거친 결정이어야 한다).
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = 'CREFLEINC/omf-mes-client'
LABELS = 'uiux→client,ready'
CHANGE_NOTICE_LABELS = 'uiux→client'  # ⛔ ready 는 착수 이슈 전용 — 변경 통지에는 붙이지 않는다

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

    ('원본 자료 경로',
     re.compile(r'docs/research/|design/raw/(?:customer|decisions|process)/'),
     '경로는 포인터라 허용이나, 원본 자료는 파일명 자체가 내용을 드러낼 수 있다'),
]

PLACEHOLDER = re.compile(r'<[가-힣][^>]*>|W-00-00|omf-mes#00|YYYY-MM-DD|v0\.0|<해시>')

SCREEN_ID = re.compile(r'\b([WPM]-(?:CO|\d{2})-\d{2})\b')

# 회신 코멘트 첫 줄 — team-issue-protocol §7.
# ⛔ 완전 일치로 잡지 않는다. §7 템플릿 자신이 「## 개발팀 전달사항 — <한 줄 결론>」이고,
#    실측에서 정본을 지킨 유일한 회신(omf-mes#206)이 바로 그 대시 형태였다.
#    완전 일치로 두면 «규약을 지킨 사람»이 막히고, 막힌 사람은 검사기를 끈다.
# 뒤가 붙으려면 공백으로 끊겨야 한다 — 「## 개발팀 전달사항입니다」 같은 변형은 막는다.
REPLY_HEAD = re.compile(r'^##[ \t]+개발팀 전달사항(?:[ \t]|$)')

# 이미 구현·병합된 화면. 「착수 가능」으로 오면 프론트가 그냥 닫는다.
# 전할 것이 있으면 ⛔/⚠ 변경 통지로 간다.
ALREADY_BUILT = {
    'W-06-07': '창고·Location 마스터',
    'W-06-01': 'Routing(공정) 등록·관리',
}


def gh_issues():
    """상대 저장소의 이슈 전건. 조회 실패는 None (막지 않되 알린다).

    --search 를 쓰지 않는다 — GitHub 검색은 인덱싱 지연이 있고 하이픈이 든
    토큰(W-06-03)에서 헛돌 수 있다. 전건을 받아 제목을 직접 맞춘다.
    """
    try:
        out = subprocess.run(
            ['gh', 'issue', 'list', '--repo', REPO, '--state', 'all',
             '--limit', '300', '--json', 'number,title,state,labels'],
            capture_output=True, timeout=30)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout.decode('utf-8'))
    except Exception:
        return None


TEAM_LABEL = re.compile(r'^Agent\s*:\s*T\d+$')


def suggest_team(screen_id, issues):
    """같은 화면·같은 도메인 이슈에서 이미 쓰인 Agent : T{n} 라벨을 세어 제안한다.

    자동 부착이 아니라 제안이다 — 팀 배정은 design-work-assignment 의 승인을 거친
    결정이어야 하고, 이 스크립트는 그 결정을 대신하지 않는다.
    """
    if not issues or not screen_id:
        return []
    domain = screen_id.split('-')[1] if '-' in screen_id else None
    same_screen, same_domain = [], []
    for i in issues:
        title = i.get('title', '')
        labels = [l['name'] for l in i.get('labels', []) if TEAM_LABEL.match(l['name'])]
        if not labels:
            continue
        if screen_id in title:
            same_screen += labels
        elif domain and re.search(r'\b[WPM]-%s-\d{2}\b' % re.escape(domain), title):
            same_domain += labels
    pool = same_screen or same_domain
    if not pool:
        return []
    counts = {}
    for l in pool:
        counts[l] = counts.get(l, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    scope = '같은 화면' if same_screen else '같은 도메인'
    return [(l, n, scope) for l, n in ranked]


def check_duplicate(screen_id, change_notice, issues=None):
    """(errs, warns, 조회했는가, issues) — issues 를 넘기면 재조회하지 않는다."""
    errs, warns = [], []

    if not change_notice and screen_id in ALREADY_BUILT:
        errs.append(('발행 금지 화면',
                     '%s %s' % (screen_id, ALREADY_BUILT[screen_id]),
                     '이미 구현·병합된 화면이다. 「착수 가능」으로 오면 프론트가 그냥 닫는다. '
                     '전할 것이 있으면 ⛔/⚠ 변경 통지로 보낸다'))

    if issues is None:
        issues = gh_issues()
    if issues is None:
        warns.append(('원격 조회 실패', 'gh issue list — %s' % REPO,
                      '중복 여부를 확인하지 못했다. gh auth status 를 보고 다시 돌리거나 '
                      '웹에서 직접 확인한 뒤 발행한다'))
        return errs, warns, False, None

    same = [i for i in issues if screen_id and screen_id in i['title']]
    for i in same:
        labels = [l['name'] for l in i.get('labels', [])]
        is_ready = 'ready' in labels or '착수 가능' in i['title']
        num = '#%d' % i['number']

        if change_notice:
            continue                      # 변경 통지는 같은 화면에 여러 건이 정상이다

        if is_ready and i['state'] == 'OPEN':
            errs.append(('중복 발행', '%s %s (열려 있음)' % (num, i['title'][:50]),
                         '같은 화면의 착수 이슈가 이미 열려 있다. 바뀐 것이 있으면 '
                         '본문을 고치지 말고 ⛔/⚠ 변경 통지를 새 이슈로 올린다'))
        elif is_ready and i['state'] == 'CLOSED':
            errs.append(('완료된 화면', '%s %s (닫힘)' % (num, i['title'][:50]),
                         '프론트가 이미 구현을 마치고 닫은 화면이다. 다시 「착수 가능」을 '
                         '보내면 안 된다 — ⛔/⚠ 변경 통지로 간다'))
        else:
            warns.append(('같은 화면의 다른 이슈', '%s %s' % (num, i['title'][:50]),
                          '변경 통지로 보인다. 착수 이슈가 이 화면에 처음이면 그대로 진행한다'))

    return errs, warns, True, issues


def print_status():
    issues = gh_issues()
    if issues is None:
        print('⛔ 조회 실패 — gh auth status 를 확인하세요.')
        return 1
    ready = [i for i in issues
             if 'ready' in [l['name'] for l in i.get('labels', [])]]
    print('착수 가능 통지 현황 — %s' % REPO)
    print('─' * 66)
    if not ready:
        print('  (아직 없음)')
    for i in sorted(ready, key=lambda x: x['number']):
        m = SCREEN_ID.search(i['title'])
        mark = '진행 중' if i['state'] == 'OPEN' else '완료'
        print('  #%-3d %-6s %-10s %s' % (i['number'], mark,
                                         m.group(1) if m else '?', i['title'][:52]))
    print('\n  발행 %d건 (진행 중 %d · 완료 %d)'
          % (len(ready),
             sum(1 for i in ready if i['state'] == 'OPEN'),
             sum(1 for i in ready if i['state'] == 'CLOSED')))
    print('\n  ⛔ 발행 금지: ' + ' · '.join('%s %s' % (k, v) for k, v in ALREADY_BUILT.items()))
    return 0


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
    if '--status' in sys.argv:
        return print_status()

    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    change_notice = '--change-notice' in sys.argv
    # 회신 코멘트 — 기존 이슈에 «코멘트»로 답하는 글이다. 새 이슈를 만들지 않으므로
    # 폼 6항목 구조도, 「같은 화면의 착수 이슈가 이미 있다」는 중복 발행 검사도 적용되지
    # 않는다(답하는 대상이 바로 그 이슈다).
    reply = '--reply' in sys.argv
    # 공개 안전 스캔은 «기본 켜짐»이다. 회신이 비공개 저장소(omf-mes)로 갈 때만 끈다 —
    # 거기서는 단가·조항 요약·내부 주소가 막을 이유가 없는데 막힌다. 기본을 켜 두는 쪽이
    # 안전한 이유는, 끄는 것을 잊으면 과하게 막힐 뿐이고 켜는 것을 잊으면 흘러나가기 때문이다.
    private = '--private' in sys.argv
    if private and not reply:
        print('⛔ --private 는 --reply 와 함께만 쓴다.')
        print('   착수·변경 통지는 언제나 공개 저장소(omf-mes-client)로 나가므로')
        print('   공개 안전 스캔을 끌 수 있는 자리가 아니다.')
        return 2
    title = None
    if '--title' in sys.argv:
        i = sys.argv.index('--title')
        if i + 1 < len(sys.argv):
            title = sys.argv[i + 1]
    team = None
    if '--team' in sys.argv:
        i = sys.argv.index('--team')
        if i + 1 < len(sys.argv):
            team = sys.argv[i + 1].strip()
            if not team.upper().startswith('T'):
                team = 'T' + team

    with io.open(path, encoding='utf-8') as f:
        text = f.read()
    secs = sections(text)

    errs, warns = ([], [])
    if not change_notice and not reply:
        errs, warns = check_structure(text, secs)

    checked_remote = False
    team_suggestions = []
    if reply:
        # 회신은 이미 있는 이슈에 다는 코멘트라 중복 발행이라는 개념이 없다.
        # checked_remote 는 비-reply 경로의 안내 문구 전용이라 손대지 않는다 —
        # 여기서 True 로 두면 「확인했다」는 거짓을 남기게 된다.
        pass
    elif '--no-remote' in sys.argv:
        warns.append(('원격 조회 생략', '--no-remote',
                      '중복 발행 여부를 확인하지 않았다. 발행 전에 반드시 직접 본다'))
    else:
        m = SCREEN_ID.search(text)
        if not m:
            warns.append(('화면 ID 인식 실패', '1번 칸',
                          '화면 ID 형식(W-06-03)을 못 찾아 중복 검사를 건너뛰었다'))
        else:
            issues = gh_issues()
            de, dw, checked_remote, issues = check_duplicate(m.group(1), change_notice, issues)
            errs += de
            warns += dw
            if not team and issues:
                team_suggestions = suggest_team(m.group(1), issues)

    left = PLACEHOLDER.findall(text)
    if left:
        errs.append(('미기입 자리표시', ' · '.join(sorted(set(left))[:6]),
                     '초안 자리표시가 남아 있다. 전부 채운다'))

    if not private:
        errs += scan(text, BLOCKING)
        warns += scan(text, ADVISORY)

    if reply:
        if change_notice:
            warns.append(('모드 충돌', '--reply --change-notice',
                          '두 모드를 함께 줬다. --reply 로 검사했다 — '
                          '변경 통지를 검사하려면 --reply 를 뺀다'))
        first = text.lstrip().split('\n')[0].strip()
        if not REPLY_HEAD.match(first):
            errs.append(('머리 표기', first[:60] or '(빈 줄)',
                         'team-issue-protocol §7 — 첫 줄은 「## 개발팀 전달사항」으로 «시작»한다. '
                         '뒤에 「 — <한 줄 결론>」을 붙여도 된다(§7 템플릿·#206 이 그 형태다). '
                         '실측에서 #232 는 「##」이 빠졌고 #222 는 구 표기를 썼다'))

    kind = '회신 코멘트' if reply else ('변경 통지' if change_notice else '착수 가능 통지')
    if reply and private:
        kind += '(비공개 — 공개 안전 스캔 끔)'
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
        print('\n%s 고치고 다시 검사하세요.'
              % ('회신 규약 위반입니다.' if private else '공개 저장소입니다.'))
        return 1

    if reply:
        print('\n✅ 게시해도 되는 상태입니다.')
        print('\n─ 게시 명령 ' + '─' * 52)
        print('gh issue comment <요청 이슈 번호> --repo <저장소> \\')
        print('  --body-file %s' % _q(path))
        print('\n⛔ gh issue create 를 쓰지 않는다 — 회신은 «요청 이슈의 코멘트»다.')
        print('   새 이슈로 내면 개발팀이 ⚠ 이상의 변경 통지로 읽어 재작업으로 오해한다.')
        return 0

    print('\n✅ 발행해도 되는 상태입니다.%s'
          % ('' if checked_remote else '  (⚠ 중복 검사는 못 했습니다)'))

    if team_suggestions:
        top = team_suggestions[0]
        print('\n💡 팀 라벨 제안 — %s 기존 이슈에 Agent : %s 가 %d건 보입니다.'
              % (top[2], top[0].split(':')[-1].strip(), top[1]))
        print('   자동 부착하지 않았습니다 — --team T{n} 을 직접 주거나, 배정이 아직이면')
        print('   design-work-assignment 로 먼저 확정하세요.')

    labels = CHANGE_NOTICE_LABELS if change_notice else LABELS
    if team:
        team_label = 'Agent : %s' % team
        labels = labels + ',' + team_label
        print('\n💡 --team %s → 라벨에 「%s」를 병기합니다.' % (team, team_label))

    if title:
        print('\n─ 발행 명령 ' + '─' * 52)
        print('gh issue create --repo %s \\' % REPO)
        print('  --title %s \\' % _q(title))
        print('  --body-file %s \\' % _q(path))
        print('  --label %s' % _q(labels))
        print('\n⚠ --label 을 빼지 마세요 — CLI 는 폼을 거치지 않아 라벨이 자동으로 붙지 않습니다.')
    else:
        print('\n(--title "…" 을 주면 gh 명령까지 만들어 줍니다)')
    return 0


def _q(s):
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == '__main__':
    sys.exit(main())

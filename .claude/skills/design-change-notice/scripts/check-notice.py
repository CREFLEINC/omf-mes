#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""설계 변동 공지 초안을 발행 «전에» 검사한다.

왜 필요한가
-----------
공지는 개발팀 저장소 둘(`CREFLEINC/omf-mes-client` · `CREFLEINC/omf-mes-server`)에 같은 본문으로
나간다. **omf-mes-client 는 공개 저장소다** — 제목·본문·첨부·라벨·수정 이력이 전부 공개되고,
지워도 인덱싱된 사본과 포크는 회수되지 않는다(2026-08-04 DS 저장소 유출 실측). 그래서 순서를
못박는다 — 초안 생성 → 검사 → 발행. 이 검사기는 되돌릴 수 없는 행위의 마지막 방어선이다.

V3(2026-09-03) 규칙 5 가 공지의 «모양»을 정했다 — 4항(날짜·배포 버전·자료 목록·달라진 지점) ·
⛔ 내용 금지 · ⛔ 백엔드/클라이언트 구분 금지. 규칙 N1~N6·T 가 그 모양을, 규칙 P 가 공개 안전을 본다.

규칙 (⛔ 는 종료 코드 1 · ⚠ 는 사람이 판단한다)
------------------------------------------------
  ⛔ N1 4항 머리 — 「1. **공지 발행 날짜**:」「2. **배포 버전**:」「3. **설계 자료 목록**」
        「4. **이전 버전(」 네 머리가 각각 정확히 1번
  ⛔ N2 해시 실재 — 2항의 전체 해시(40 hex)와 4항 머리의 since 해시7 이 `git cat-file -e` 로
        실재. `--no-git` 이면 형식만(40 hex / 7 hex · 괄호 안 해시7 = 전체 해시 앞 7자)
  ⛔ N3 팀 구분어 — 인라인 코드(백틱)를 걷어낸 본문에 「백엔드」「클라이언트」「프론트」「서버팀」
        (V3 「백엔드, 클라이언트 개발팀을 구분해서 공지를 작성하지마라. 괜한 실수를 만든다」)
  ⛔ N4 내용 유출 — 코드 펜스(```) · 화살표(→ · -> · =>) · 행머리 `>` 인용 · 4항 항목의 백틱 밖
        `:`(값 서술 징후 — 백틱 안은 `POST /x/{id}:approve` 같은 경로라 제외)
  ⚠ N5 4항 항목이 160자 초과 — 지점이 아니라 설명일 가능성(생성기는 160자에서 줄을 나눈다)
  ⛔ N6 자리표시 — `<한글>` · W-00-00 · omf-mes#00 · YYYY-MM-DD · v0.0 · <해시> · `(?, …)`
  ⛔ P  공개 안전 — 옛 check-issue.py 의 BLOCKING 10종 그대로(이미지·조항 요약·확정 기록 마커·
        실 사번·실 LOT·인프라·금액·인용·내부 이름·발행 전 지시 잔재) · ⚠ ADVISORY 5종
  ⛔ T  제목(`--title`) — `[설계 변동 공지] YYYY-MM-DD · 해시7` 이고 날짜·해시7 이 본문 1·2항과 같다

사용법
------
    python3 check-notice.py tmp/notices/2026-09-03-abc1234.md
    python3 check-notice.py <초안.md> --title "[설계 변동 공지] 2026-09-03 · abc1234"   # 통과 시 gh 명령 출력
    python3 check-notice.py <초안.md> --no-git --repo-root <경로>                        # 시험용

출력 — 위반마다 「⛔/⚠ 규칙 행번호: 설명」 한 줄. 통과하면 「✅ 통과」 와 발행 명령 두 줄을
**출력만** 한다 — 실행은 사람 게이트(SKILL.md ④) 뒤에서 사람이 한다.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))

CLIENT_REPO = "CREFLEINC/omf-mes-client"     # PUBLIC  (실측 2026-09-03)
SERVER_REPO = "CREFLEINC/omf-mes-server"     # PRIVATE (실측 2026-09-03) — 같은 본문이 나가므로 공개 기준 하나로 검사한다
NOTICE_LABEL = "설계 변동 공지"
CLIENT_FILTER_LABEL = "uiux→client"          # 클라이언트 저장소의 기존 필터 라벨 — 함께 붙인다

HEADS = [
    ("1항", re.compile(r"^1\. \*\*공지 발행 날짜\*\*: *(\S+)")),
    ("2항", re.compile(r"^2\. \*\*배포 버전\*\*: *`([0-9a-f]+)` *\(`([0-9a-f]+)`\)")),
    ("3항", re.compile(r"^3\. \*\*설계 자료 목록\*\*")),
    ("4항", re.compile(r"^4\. \*\*이전 버전\(`([0-9a-f]+)`\)과 달라진 지점\*\*")),
]
HEAD_LOOSE = [
    ("1항", re.compile(r"^1\. \*\*공지 발행 날짜\*\*:")),
    ("2항", re.compile(r"^2\. \*\*배포 버전\*\*:")),
    ("3항", re.compile(r"^3\. \*\*설계 자료 목록\*\*")),
    ("4항", re.compile(r"^4\. \*\*이전 버전\(")),
]
TITLE = re.compile(r"^\[설계 변동 공지\] (\d{4}-\d{2}-\d{2}) · ([0-9a-f]{7})$")
TEAM_WORDS = re.compile(r"백엔드|클라이언트|프론트|서버팀")
ARROWS = re.compile(r"→|->|=>")
INLINE_CODE = re.compile(r"`[^`\n]*`")
ITEM_MAX = 160

# ─── 공개 안전 — 옛 check-issue.py(BLOCKING 10 · ADVISORY 5 · PLACEHOLDER) 를 그대로 이식했다.
#     omf-mes-client 는 공개 저장소다. 정규식·설명을 바꾸지 않았다 — 「무엇을 잡느냐」가 실측
#     사고(2026-08-04 DS 유출 · omf-mes-client#602·#603 초안 잔재)로 굳은 것이라 여기서 다시
#     판단하지 않는다. 내부 이름 목록에 V3 로 생긴 스킬 이름 둘만 더했다.

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

    # ⭐ 2026-08-31 신설 — 「초안 잔재」. 위 항목들이 «내용 유출»을 보는 것과 달리
    #    이것은 «초안이 안 끝났다»를 본다. 실측 사고: omf-mes-client#602·#603 이
    #    발행 전 자기검토 문구를 단 채 공개 저장소로 나갔다.
    ('내부 에이전트·스킬 이름',
     re.compile(r'design-review-analyst|design-doc-writer|design-review-intake'
                r'|uiux-client-handoff|team-issue-protocol'
                r'|design-change-notice|design-request-intake'),
     '우리 하네스의 내부 이름이다. 받는 쪽에게 뜻이 없고 내부 절차를 드러낸다 — 지운다'),

    ('발행 전 지시 잔재',
     re.compile(r'발행\s*(?:전|하기\s*전)[^\n]{0,30}?(?:확인|검토|권장)'),
     '이미 발행된 글에 「발행 전에 …하라」가 남아 있다. 초안 메모다 — 지우고, '
     '정말 확인이 안 끝났으면 발행을 미룬다'),
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

    # ⚠ 막지 않는다 — 받는 쪽에게 「여기까지만 확인했다」를 정직하게 알리는 것은 정당하다.
    #    다만 omf-mes-client#602·#603 에서는 그것이 «발행 전 자기검토» 잔재였다.
    ('자기 미확인 자인',
     re.compile(r'확인하지\s*못했|확인\s*못\s*했|일부만\s*확인'),
     '받는 쪽에게 한계를 알리는 문장이면 허용. 발행 전 자기검토 메모가 남은 것이면 지운다 '
     '— 「확인이 안 끝났다」가 사실이면 발행을 미루는 쪽이 맞다'),
]

# 미기입 자리표시 — 「(?, #14)」 형태는 omf-mes-client#602 가 표 칸을 못 채운 채 발행된 실측 사례다.
PLACEHOLDER = re.compile(r'<[가-힣][^>]*>|W-00-00|omf-mes#00|YYYY-MM-DD|v0\.0|<해시>'
                         r'|\(\s*\?\s*[,)]')


# ─────────────────────────────────────────── 보조

def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def strip_inline_code(s: str) -> str:
    return INLINE_CODE.sub("`", s)


def scan(text: str, rules) -> list:
    """(이름, 행번호, 설명) — 규칙마다 «모든» 일치를 낸다(첫 건만 내면 나머지를 못 본다)."""
    hits = []
    for name, rx, fix in rules:
        for m in rx.finditer(text):
            hits.append((name, _line_of(text, m.start()), fix))
    return hits


def commit_exists(root: str, sha: str) -> bool:
    r = subprocess.run(["git", "-c", "core.quotepath=false", "cat-file", "-e", sha + "^{commit}"],
                       cwd=root, capture_output=True)
    return r.returncode == 0


def item_lines(lines: list) -> list:
    """4항 머리 뒤의 `- ` 항목 — [(행번호, 본문)]."""
    out, in4 = [], False
    for n, line in enumerate(lines, 1):
        if HEAD_LOOSE[3][1].match(line):
            in4 = True
            continue
        if in4 and line.startswith("- "):
            out.append((n, line))
    return out


# ─────────────────────────────────────────── 검사

def check(text: str, title: str | None = None, use_git: bool = True,
          root: str = DEFAULT_ROOT) -> tuple:
    """(errs, warns) — 각 항목은 (규칙코드, 행번호, 설명)."""
    errs, warns = [], []
    lines = text.splitlines()

    # N1 — 4항 머리 각 1번
    fields = {}
    for (name, strict), (_, loose) in zip(HEADS, HEAD_LOOSE):
        hits = [(n, l) for n, l in enumerate(lines, 1) if loose.match(l)]
        if len(hits) != 1:
            errs.append(("N1", hits[0][0] if hits else 0,
                         "%s 머리가 %d번 — 정확히 1번이어야 한다" % (name, len(hits))))
            continue
        n, l = hits[0]
        m = strict.match(l)
        if not m:
            errs.append(("N1", n, "%s 머리의 형식이 다르다 — 생성기 출력 그대로여야 한다" % name))
            continue
        fields[name] = (n, m.groups())

    # N2 — 해시 실재
    if "2항" in fields:
        n, (full, short) = fields["2항"]
        if not re.fullmatch(r"[0-9a-f]{40}", full):
            errs.append(("N2", n, "배포 버전은 전체 해시(40 hex)여야 한다: %s" % full))
        elif not re.fullmatch(r"[0-9a-f]{7}", short) or full[:7] != short:
            errs.append(("N2", n, "괄호 안 해시7 이 전체 해시의 앞 7자와 다르다"))
        elif use_git and not commit_exists(root, full):
            errs.append(("N2", n, "배포 버전 커밋이 저장소에 없다: %s" % full))
    if "4항" in fields:
        n, (since,) = fields["4항"]
        if not re.fullmatch(r"[0-9a-f]{7}", since):
            errs.append(("N2", n, "이전 버전은 해시7 이어야 한다: %s" % since))
        elif use_git and not commit_exists(root, since):
            errs.append(("N2", n, "이전 버전 커밋이 저장소에 없다: %s" % since))
    if "1항" in fields:
        n, (date,) = fields["1항"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            errs.append(("N1", n, "공지 발행 날짜는 YYYY-MM-DD 다: %s" % date))

    # N3 — 팀 구분어(백틱 밖)
    for n, line in enumerate(lines, 1):
        for m in TEAM_WORDS.finditer(strip_inline_code(line)):
            errs.append(("N3", n, "팀 구분어 「%s」 — 공지는 팀을 가르지 않는다(V3 규칙 5)" % m.group(0)))

    # N4 — 내용 유출
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            errs.append(("N4", n, "코드 펜스 — 본문·값을 옮긴 징후. 지점(이름·키·절)만 적는다"))
        if ARROWS.search(line):
            errs.append(("N4", n, "화살표(→ · -> · =>) — 「무엇이 어떻게 바뀌었나」를 적은 징후"))
        if line.startswith(">"):
            errs.append(("N4", n, "행머리 `>` 인용 — 문서 본문을 옮긴 징후"))
    items = item_lines(lines)
    for n, line in items:
        if ":" in strip_inline_code(line):
            errs.append(("N4", n, "4항 항목의 백틱 밖 `:` — 값 서술 징후. 지점만 적는다"))

    # N5 — 항목 길이
    for n, line in items:
        if len(line) > ITEM_MAX:
            warns.append(("N5", n, "4항 항목이 %d자(>%d) — 지점이 아니라 설명일 가능성"
                          % (len(line), ITEM_MAX)))

    # N6 — 자리표시
    for m in PLACEHOLDER.finditer(text):
        errs.append(("N6", _line_of(text, m.start()), "자리표시 「%s」 가 남아 있다" % m.group(0)))

    # P — 공개 안전
    for name, n, fix in scan(text, BLOCKING):
        errs.append(("P", n, "[%s] %s" % (name, fix)))
    for name, n, fix in scan(text, ADVISORY):
        warns.append(("P", n, "[%s] %s" % (name, fix)))

    # T — 제목
    if title is not None:
        m = TITLE.match(title)
        if not m:
            errs.append(("T", 0, "제목 형식 — 「[설계 변동 공지] YYYY-MM-DD · 해시7」: %s" % title))
        else:
            if "1항" in fields and fields["1항"][1][0] != m.group(1):
                errs.append(("T", fields["1항"][0], "제목의 날짜 %s 가 1항 %s 과 다르다"
                             % (m.group(1), fields["1항"][1][0])))
            if "2항" in fields and fields["2항"][1][1] != m.group(2):
                errs.append(("T", fields["2항"][0], "제목의 해시7 %s 이 2항 %s 과 다르다"
                             % (m.group(2), fields["2항"][1][1])))

    errs.sort(key=lambda e: (e[1], e[0]))
    warns.sort(key=lambda e: (e[1], e[0]))
    return errs, warns


def _q(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def publish_commands(title: str, path: str) -> list:
    return [
        "gh issue create --repo %s --title %s --body-file %s --label %s --label %s"
        % (CLIENT_REPO, _q(title), _q(path), _q(NOTICE_LABEL), _q(CLIENT_FILTER_LABEL)),
        "gh issue create --repo %s --title %s --body-file %s --label %s"
        % (SERVER_REPO, _q(title), _q(path), _q(NOTICE_LABEL)),
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="설계 변동 공지 초안 검사기")
    ap.add_argument("path", help="공지 초안 .md")
    ap.add_argument("--title", help="발행 제목 — 주면 형식·본문 일치를 검사하고 통과 시 gh 명령을 출력")
    ap.add_argument("--no-git", action="store_true", help="해시 실재 검사 생략(시험용)")
    ap.add_argument("--repo-root", default=DEFAULT_ROOT)
    a = ap.parse_args(argv)

    with io.open(a.path, encoding="utf-8") as fh:
        text = fh.read()
    errs, warns = check(text, a.title, not a.no_git, os.path.abspath(a.repo_root))

    for code, n, msg in warns:
        print("⚠ %s %d: %s" % (code, n, msg))
    for code, n, msg in errs:
        print("⛔ %s %d: %s" % (code, n, msg))
    if errs:
        print("⛔ 위반 %d건 · 확인 %d건 — 고치고 다시 검사한다. 발행하지 않는다." % (len(errs), len(warns)))
        return 1

    print("✅ 통과%s" % (" (⚠ 확인 %d건 — 사람이 본다)" % len(warns) if warns else ""))
    if a.title:
        print("")
        print("─ 발행 명령 — 사람 게이트(초안 전문 승인) 뒤에 사람이 실행한다. 출력만 한다 ─")
        for cmd in publish_commands(a.title, a.path):
            print(cmd)
        print("⚠ 라벨 「%s」 가 저장소에 없으면 먼저 `gh label create` — 이것도 승인 게이트다." % NOTICE_LABEL)
    else:
        print("(--title \"[설계 변동 공지] YYYY-MM-DD · 해시7\" 을 주면 발행 명령까지 낸다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

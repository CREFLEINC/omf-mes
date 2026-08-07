#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 화면 정본 대조 — 인벤토리와 통합 IA 가 같은 화면을 말하는가.
#
# 왜 필요한가
#   화면을 신설하면 고칠 자리가 넷이다 — 두 문서 × (메뉴 트리 + 화면표).
#   표만 맞추고 트리를 빠뜨리면 **메뉴에 없는 화면**이 되는데, 두 문서의 표를
#   대조하는 것으로는 잡히지 않는다. v1.7 에서 실제로 그 누락이 났다.
#
# 무엇을 보나
#   ① 각 문서 안에서 메뉴 트리 ↔ 화면표가 같은 집합인가
#   ② 두 문서가 같은 화면 집합을 갖는가
#   ③ 인벤토리 §1 요약 표의 숫자가 실제 계수와 맞는가
#
# 표준 라이브러리만 쓴다(저장소 관행).
import io
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
INVENTORY = os.path.join(HERE, '..', 'uiux', '2026-07-25-화면목록-IA', 'screen-inventory-ia.md')
INTEGRATED = os.path.join(HERE, '04-통합-IA.md')

SCREEN = re.compile(r'([WMP]-(?:CO|\d{2})-\d{2})')
PROGRAM = {'W': '관리웹', 'P': 'POP', 'M': '모바일'}


def read(path):
    with io.open(path, encoding='utf-8') as f:
        return f.read()


def section(text, start_pattern, end_pattern):
    """두 제목 사이를 잘라낸다. 끝 제목이 없으면 파일 끝까지."""
    begin = re.search(start_pattern, text, re.M)
    if begin is None:
        raise ValueError('시작 제목을 찾지 못했다: %s' % start_pattern)
    end = re.search(end_pattern, text[begin.end():], re.M)
    return text[begin.start():begin.end() + end.start()] if end else text[begin.start():]


def from_table(block):
    """표 행의 첫 칸에서 화면 ID 를 모은다."""
    out = []
    for line in block.split('\n'):
        if not line.startswith('|'):
            continue
        head = line.strip('|').split('|')[0]
        found = SCREEN.findall(head)
        if found:
            out.append(found[0])
    return out


def from_tree(block):
    """메뉴 트리 줄(- 로 시작)의 괄호 안 화면 ID 를 모은다."""
    out = []
    for line in block.split('\n'):
        if not line.lstrip().startswith('-'):
            continue
        out.extend(SCREEN.findall(line))
    return out


def compare(label, tree, table, errors):
    only_tree = sorted(set(tree) - set(table))
    only_table = sorted(set(table) - set(tree))
    if only_tree:
        errors.append('%s — 트리에만 있다: %s' % (label, ' '.join(only_tree)))
    if only_table:
        errors.append('%s — 표에만 있다(메뉴에 없는 화면): %s' % (label, ' '.join(only_table)))
    duplicated = [s for s, n in Counter(table).items() if n > 1]
    if duplicated:
        errors.append('%s — 표에 중복: %s' % (label, ' '.join(sorted(duplicated))))


def check_summary(text, screens, errors):
    """인벤토리 §1 요약 표의 합계 행이 실제 계수와 맞는가."""
    row = re.search(r'^\| \*\*합계\*\* \|(.+)$', text, re.M)
    if row is None:
        errors.append('요약 — 합계 행을 찾지 못했다')
        return
    numbers = [int(n) for n in re.findall(r'\d+', row.group(1))]
    if len(numbers) < 4:
        errors.append('요약 — 합계 행에서 숫자 4개를 읽지 못했다')
        return
    counted = Counter(s[0] for s in screens)
    expected = [counted['W'], counted['P'], counted['M'], len(screens)]
    if numbers[:4] != expected:
        errors.append('요약 — 합계 행 %s ↔ 실제 %s (관리웹·POP·모바일·계)'
                      % (numbers[:4], expected))


def main():
    errors = []

    inventory = read(INVENTORY)
    inv_tree = (from_tree(section(inventory, r'^### 2\.1 ', r'^### 2\.2 '))
                + from_tree(section(inventory, r'^### 2\.2 ', r'^### 2\.3 '))
                + from_tree(section(inventory, r'^### 2\.3 ', r'^## 3\. ')))
    inv_table = from_table(section(inventory, r'^## 3\. ', r'^## 4\. '))
    compare('인벤토리', inv_tree, inv_table, errors)
    check_summary(inventory, inv_table, errors)

    integrated = read(INTEGRATED)
    int_tree, int_table = [], []
    for start, end in ((r'^## §3\. ', r'^## §4\. '),
                       (r'^## §4\. ', r'^## §5\. '),
                       (r'^## §5\. ', r'^## §6\. ')):
        block = section(integrated, start, end)
        int_tree += from_tree(block)
        int_table += from_table(block)
    compare('통합 IA', int_tree, int_table, errors)

    only_inv = sorted(set(inv_table) - set(int_table))
    only_int = sorted(set(int_table) - set(inv_table))
    if only_inv:
        errors.append('두 문서 — 인벤토리에만 있다: %s' % ' '.join(only_inv))
    if only_int:
        errors.append('두 문서 — 통합 IA 에만 있다: %s' % ' '.join(only_int))

    counted = Counter(s[0] for s in inv_table)
    print('화면 %d — %s' % (len(inv_table),
                           ' · '.join('%s %d' % (PROGRAM[k], counted[k]) for k in 'WPM')))
    if not errors:
        print('✅ 트리·표·요약이 모두 맞습니다.')
        return 0
    print('⛔ 불일치 %d건' % len(errors))
    for e in errors:
        print('  %s' % e)
    return 1


if __name__ == '__main__':
    sys.exit(main())

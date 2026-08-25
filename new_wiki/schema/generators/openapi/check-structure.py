# -*- coding: utf-8 -*-
"""OpenAPI 정본의 구조를 검사한다.

왜 필요한가
  정본은 손으로 고칠 수 있고 파일 하나가 1만 줄을 넘는다. 끊긴 `$ref` 하나,
  선언을 빠뜨린 경로 변수 하나가 눈으로는 안 보이고 목 서버·타입 생성에서 터진다.
  `check-public-safe.py` 는 **공개돼도 되는가**만 본다. 이 검사기는 **계약으로서
  성립하는가**를 본다.

무엇을 막나
  ① 끊긴 `$ref` — 참조한 스키마·파라미터가 없다
  ② 참조되지 않는 스키마 — 죽은 정의는 쓰이지 않는 타입을 만든다
  ③ `required` 인데 `properties` 에 없는 필드
  ④ `example` 없는 프로퍼티 — 목 도구가 `"string"` 을 내면 화면 검증이 안 된다
     예외를 둬야 하면 `"x-no-example": "<이유>"` 를 그 프로퍼티에 적는다. 키 구조가
     정해지지 않은 자유 형식 객체가 그런 경우다 — 예시를 만들면 없는 키를 지어내게 된다
  ⑤ 경로 템플릿 변수 ↔ `parameters` 선언 불일치
  ⑥ `summary` · `tags` · `responses` 누락, GET 의 `requestBody`
  ⑦ 선언되지 않은 `tag`
  ⑧ 쓰기 오퍼레이션에 `Idempotency-Key` 없음 — 재전송이 전표를 두 번 만든다
  ⑨ `If-Match` 를 받는데 409 를 선언하지 않음 — 저장 충돌을 400 과 섞게 된다

사용법
  python3 check-structure.py [spec.json ...]
  인자를 생략하면 이 폴더의 정본 전부를 검사한다.
  통과하면 0, 위반이 있으면 1 을 돌려준다.
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 new_wiki/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")
# ⛔ 2026-08-11 정정 — patch 가 빠져 있었다. 02 계약이 처음 PATCH 를 쓰면서 드러났다.
#    앞의 세 계약에 PATCH 가 0건이라 구멍이 안 보였을 뿐, PATCH 오퍼레이션은
#    멱등키·example·409 검사를 통째로 빠져나가고 있었다.
WRITE_METHODS = ('post', 'put', 'patch', 'delete')
ALL_METHODS = ('get',) + WRITE_METHODS
PATH_VAR = re.compile(r'\{(\w+)\}')

# 다른 스키마에서만 참조되고 경로에서 직접 쓰이지 않아도 되는 것.
# ErrorItem 은 ErrorResponse 안에서만 쓰인다.
REFERENCED_INDIRECTLY = {'ErrorItem'}


def collect_refs(node: object, out: set) -> set:
    """문서 전체에서 쓰인 `$ref` 대상 이름을 모은다."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == '$ref' and isinstance(value, str):
                out.add(value)
            else:
                collect_refs(value, out)
    elif isinstance(node, list):
        for value in node:
            collect_refs(value, out)
    return out


def path_params(item: dict, operation: dict) -> set:
    """경로 수준과 오퍼레이션 수준에 선언된 path 파라미터 이름."""
    names = set()
    for source in (item.get('parameters', []), operation.get('parameters', [])):
        for param in source:
            if isinstance(param, dict) and param.get('in') == 'path':
                names.add(param['name'])
    return names


def param_refs(operation: dict) -> list:
    return [p.get('$ref', '') for p in operation.get('parameters', []) if isinstance(p, dict)]


def check_schemas(spec: dict, used: set) -> list:
    errors = []
    schemas = spec['components']['schemas']
    for name, schema in schemas.items():
        properties = set((schema.get('properties') or {}).keys())
        for field in schema.get('required', []):
            if field not in properties:
                errors.append('required 인데 properties 에 없다 — %s.%s' % (name, field))
        for field, definition in (schema.get('properties') or {}).items():
            if '$ref' in definition or definition.get('type') == 'array':
                continue
            if 'example' in definition or 'x-no-example' in definition:
                continue
            errors.append('example 없음 — %s.%s' % (name, field))

    for ref in sorted(used):
        target = ref.split('/')[-1]
        if ref.startswith('#/components/schemas/') and target not in schemas:
            errors.append('끊긴 $ref — %s' % ref)
        if ref.startswith('#/components/parameters/') and target not in spec['components'].get('parameters', {}):
            errors.append('끊긴 $ref — %s' % ref)

    referenced = {ref.split('/')[-1] for ref in used}
    for name in sorted(set(schemas) - referenced - REFERENCED_INDIRECTLY):
        errors.append('참조되지 않는 스키마 — %s' % name)
    return errors


def check_paths(spec: dict) -> list:
    errors = []
    declared_tags = {tag['name'] for tag in spec.get('tags', [])}
    for path, item in spec['paths'].items():
        for method in ALL_METHODS:
            operation = item.get(method)
            if not operation:
                continue
            label = '%s %s' % (method.upper(), path)

            wanted = set(PATH_VAR.findall(path))
            declared = path_params(item, operation)
            if wanted - declared:
                errors.append('경로 변수 미선언 — %s → %s' % (label, sorted(wanted - declared)))
            if declared - wanted:
                errors.append('선언됐으나 경로에 없다 — %s → %s' % (label, sorted(declared - wanted)))

            if not operation.get('summary'):
                errors.append('summary 없음 — %s' % label)
            if not operation.get('responses'):
                errors.append('responses 없음 — %s' % label)
            for tag in operation.get('tags') or ['']:
                if tag not in declared_tags:
                    errors.append('선언되지 않은 tag — %s (%s)' % (tag or '없음', label))

            if method == 'get':
                if 'requestBody' in operation:
                    errors.append('GET 에 requestBody — %s' % label)
                continue

            refs = param_refs(operation)
            if not any('IdempotencyKey' in ref for ref in refs):
                errors.append('쓰기인데 Idempotency-Key 없음 — %s' % label)
            if any('IfMatchVersion' in ref for ref in refs) and '409' not in operation['responses']:
                errors.append('If-Match 를 받는데 409 미선언 — %s' % label)
    return errors


# 설명문 자리에 쓰이는 낱말 — OpenAPI·JSON Schema 의 «주석» 키워드다.
ANNOTATION_KEYS = ('description', 'summary', 'title')

# 이 키«아래»의 이름들은 사용자가 지은 것이다 — 키워드로 읽지 않는다.
NAME_MAPS = ('properties', 'headers', 'schemas', 'parameters', 'responses',
             'requestBodies', 'securitySchemes', 'examples', 'paths')


def check_annotations(node: object, path: str = '$', in_names: bool = False) -> list:
    """주석 키워드가 «문자열»인가.

    ⛔ 왜 필요한가 — 파이썬 괄호 안에 후행 쉼표를 하나 남기면 문자열이 튜플이
    되고, 계약에는 문자열 대신 **배열**이 실린다(2026-08-24 실제 발생).
    OpenAPI 3.1 은 JSON Schema 2020-12 라 이 자리는 반드시 문자열이며,
    구현팀의 타입 생성기가 이 값을 주석으로 그대로 옮긴다.

    ⚠ 공개 안전성 검사기가 이것을 못 잡는다 — `isinstance(v, str)` 인 것만
    걷으므로 **문자열이 아니면 검사 자체를 건너뛴다.** 「통과했다」와
    「검사를 받았다」가 갈리는 자리라 여기서 막는다.

    ⛔⛔ 「이름」과 「키워드」를 가른다 — 이것을 안 가르면 오탐이 쏟아진다.
    `properties` · `headers` 아래의 키는 **사용자가 지은 이름**이라
    `description` 이라는 «필드»가 있으면 그 값은 스키마 객체(dict)가 정상이다.
    실측 — 그렇게 생긴 자리가 계약 일곱 벌에 **12곳** 있다
    (`Role.properties.description` · `Notice.properties.title` 등).
    """
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            # 이 자리의 키가 «이름»이면 주석 키워드로 보지 않는다.
            if not in_names and key in ANNOTATION_KEYS and not isinstance(value, str):
                out.append('%s.%s 가 문자열이 아니다 — %s'
                           % (path, key, type(value).__name__))
            out += check_annotations(value, '%s.%s' % (path, key),
                                     in_names=key in NAME_MAPS)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            out += check_annotations(value, '%s[%d]' % (path, index))
    return out


def check(path: str) -> int:
    spec = json.load(io.open(path, encoding='utf-8'))
    used = collect_refs(spec, set())
    errors = check_schemas(spec, used) + check_paths(spec) + check_annotations(spec)

    operations = sum(1 for item in spec['paths'].values() for m in item if m in ALL_METHODS)
    print('%s — 경로 %d · 오퍼레이션 %d · 스키마 %d'
          % (os.path.basename(path), len(spec['paths']), operations, len(spec['components']['schemas'])))
    if not errors:
        print('✅ 계약으로 성립합니다.')
        return 0
    print('⛔ 위반 %d건' % len(errors))
    for error in errors:
        print('  %s' % error)
    return 1


def main() -> int:
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(CONTRACTS_DIR, '*.json')))
    if not targets:
        print('검사할 정본이 없습니다.')
        return 1
    return max(check(target) for target in targets)


if __name__ == '__main__':
    sys.exit(main())

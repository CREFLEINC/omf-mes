#!/usr/bin/env python3
"""#213 상태 정의 인벤토리. enum 부재는 미정 판정이 아니다.

속성 및 파라미터 이름이 statusCode 또는 *StatusCode인 정의 위치를 센다.
인라인·배열·조합 하위 속성도 포함하되 참조 사용 횟수를 펼쳐 세지 않는다.
--json은 위치·사전 소유·값·제외 사유를 출력한다. 제외 사유가 있다는 사실은
업무 의미가 확정되었다는 뜻이 아니다. 사유의 적합성과 상태 전이는 사람이 검토한다.
설명 누락·판정 누락·잘못된 참조는 종료 1, 정상은 0이다. 항상 읽기 전용이다.
"""

from __future__ import annotations

import argparse
import importlib
import json
from collections import Counter
from pathlib import Path
from typing import Iterator

DICTIONARY = importlib.import_module("check-code-dictionary")
CONTRACT_DIR = Path(DICTIONARY.CONTRACTS).parent
DATA_KEYS = {"example", "examples", "default", "enum", "const"}


def is_status(name: str) -> bool:
    """상태 코드의 역사적 집계 이름 규칙을 적용한다."""
    return name == "statusCode" or name.endswith("StatusCode")


def pointer_part(name: str) -> str:
    """JSON Pointer 경로 조각을 이스케이프한다."""
    return name.replace("~", "~0").replace("/", "~1")


def definitions(node: object, path: str = "") -> Iterator[tuple[str, str, dict]]:
    """실제 속성·파라미터 정의만 순회하고 예시 데이터는 제외한다."""
    if isinstance(node, list):
        for index, child in enumerate(node):
            yield from definitions(child, f"{path}/{index}")
    elif isinstance(node, dict):
        if node.get("in") and is_status(str(node.get("name", ""))):
            yield "parameter", path, node
        for key, child in node.items():
            if key in DATA_KEYS or key.startswith("x-"):
                continue
            child_path = f"{path}/{pointer_part(key)}"
            if key == "properties" and isinstance(child, dict):
                for name, schema in child.items():
                    if is_status(name) and isinstance(schema, dict):
                        yield "property", f"{child_path}/{pointer_part(name)}", schema
            yield from definitions(child, child_path)


def resolve(node: dict, document: dict, seen: tuple = ()) -> dict:
    """로컬 참조의 설명·분류를 읽는다. 해석 불가능한 참조는 실패한다."""
    if "oneOf" in node or "anyOf" in node:
        raise ValueError("상태 자체의 oneOf/anyOf 분류는 수동 검토 필요")
    if "allOf" in node:
        combined = {}
        for branch in node["allOf"]:
            resolved = resolve(branch, document, seen)
            for key in ("description", "x-code-key", "x-no-code-key", "enum"):
                if key not in resolved:
                    continue
                value = resolved[key]
                if key in combined and combined[key] != value:
                    if key == "description":
                        value = f"{combined[key]} / {value}"
                    elif key == "enum":
                        value = [item for item in combined[key] if item in value]
                    else:
                        raise ValueError(f"allOf 분류 충돌: {key}")
                combined[key] = value
        node = combined | {key: value for key, value in node.items() if key != "allOf"}
    reference = node.get("$ref")
    if reference is None:
        return node
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise ValueError(f"로컬 참조 아님: {reference}")
    if reference in seen:
        raise ValueError(f"순환 참조: {reference}")
    target = document
    try:
        for part in reference[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
    except (KeyError, TypeError) as error:
        raise ValueError(f"참조 대상 없음: {reference}") from error
    if not isinstance(target, dict):
        raise ValueError(f"객체가 아닌 참조: {reference}")
    return resolve(target, document, (*seen, reference)) | {
        key: value for key, value in node.items() if key != "$ref"
    }


def inventory(document: dict, dictionary: dict, contract: str = "") -> list[dict]:
    """위치별 분류와 검사 결과를 반환한다. 사전 값 목록을 복제하지 않는다."""
    rows = []
    for kind, path, original in definitions(document):
        problems = []
        try:
            node = resolve(original, document)
            schema = (
                resolve(node.get("schema", {}), document)
                if kind == "parameter"
                else node
            )
        except ValueError as error:
            node, schema = original, {}
            problems.append(str(error))
        description = node.get("description")
        if not isinstance(description, str) or not description.strip():
            problems.append("설명 누락")
        keys = node.get("x-code-key", [])
        keys = [keys] if isinstance(keys, str) else keys
        if not isinstance(keys, list) or any(not isinstance(key, str) for key in keys):
            problems.append("잘못된 사전 키 형식")
            keys = []
        reason = node.get("x-no-code-key")
        excluded = isinstance(reason, str) and bool(reason.strip())
        if keys and excluded:
            problems.append("사전 키와 제외 사유 동시 지정")
        if not keys and not excluded:
            problems.append("분류 누락")
        for key in keys:
            if key not in dictionary:
                problems.append(f"사전에 없는 키: {key}")
        rows.append(
            {
                "contract": contract,
                "kind": kind,
                "pointer": path,
                "description": description,
                "enum": schema.get("enum"),
                "keys": keys,
                "owners": [
                    dictionary[key]["owner"] for key in keys if key in dictionary
                ],
                "values": {
                    key: sorted(dictionary[key]["values"])
                    for key in keys
                    if key in dictionary
                },
                "exclusion_reason": reason,
                "problems": problems,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    """현재 계약 전건 또는 명시한 파일을 검사한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument(
        "--json", action="store_true", help="전건 인벤토리를 JSON으로 출력"
    )
    args = parser.parse_args(argv)
    paths = args.paths or sorted(CONTRACT_DIR.glob("*.json"))
    if not paths:
        parser.error("검사할 계약 없음")
    dictionary = {
        row["key"]: row for row in DICTIONARY.read_dictionary(DICTIONARY.DICT)
    }
    rows = []
    for path in paths:
        rows.extend(
            inventory(
                json.loads(path.read_text(encoding="utf-8")), dictionary, path.name
            )
        )
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(f"상태 정의 {len(rows)}곳 — {dict(Counter(row['kind'] for row in rows))}")
        print(
            f"사전 연결 {sum(bool(row['keys']) for row in rows)} · "
            f"제외 사유 {sum(bool(row['exclusion_reason']) for row in rows)} · "
            f"enum {sum(row['enum'] is not None for row in rows)}"
        )
        print("enum 없음 ≠ 미정. 제외 사유 ≠ 업무 의미 확정. 전건 근거: --json")
        for row in rows:
            if row["problems"]:
                print(
                    f"{row['contract']}#{row['pointer']}: {', '.join(row['problems'])}"
                )
        print(f"위반 {sum(len(row['problems']) for row in rows)}건")
    return int(any(row["problems"] for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())

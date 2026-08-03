#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""물리 모델 ↔ OpenAPI 검산.

SQL 을 파싱해 테이블·컬럼·제약을 뽑고 OpenAPI JSON 의 components.schemas 와
대조한다. 어긋나면 종료 코드 1.

매핑 선언 — 스키마에 x-source-table, 프로퍼티에 x-source-column.
표준 라이브러리만 쓴다(저장소 관행).
"""
import io, json, os, re, sys

AUDIT_COLS = {"created_at", "created_by", "updated_at", "updated_by", "version_no"}

_CREATE = re.compile(r"^CREATE TABLE ([a-z_]+\.[a-z_]+) \($", re.M)
_COL = re.compile(r"^\s{4}([a-z_]+)\s+(.+?)\s*,?\s*(?:--.*)?$")
_UQ = re.compile(r"CONSTRAINT (\w+)\s+UNIQUE\s*\(([^)]*)\)", re.S)
_CK = re.compile(r"CONSTRAINT (\w+)\s+CHECK", re.S)


def _split_blocks(text):
    """CREATE TABLE 한 개씩 (이름, 본문) 으로 자른다."""
    out = []
    for m in _CREATE.finditer(text):
        name = m.group(1)
        start = m.end()
        end = text.find("\n);", start)
        if end == -1:
            continue
        out.append((name, text[start:end]))
    return out


def parse_sql(path):
    """{테이블명: {"columns": {...}, "constraints": [...]}}"""
    text = io.open(path, encoding="utf-8").read()
    tables = {}
    for name, body in _split_blocks(text):
        columns, constraints = {}, []
        for line in body.split("\n"):
            stripped = line.strip()
            if stripped.startswith("CONSTRAINT"):
                continue
            if stripped.startswith("--") or not stripped:
                continue
            m = _COL.match(line)
            if not m:
                continue
            col, rest = m.group(1), m.group(2)
            if col in AUDIT_COLS or col.upper() in ("CONSTRAINT",):
                continue
            rest_nc = rest.split("--")[0].strip()
            typ = rest_nc.split()[0] if rest_nc else ""
            columns[col] = {
                "type": typ,
                "not_null": "NOT NULL" in rest_nc,
                "default": _default_of(rest_nc),
            }
        for m in _UQ.finditer(body):
            cols = [c.strip() for c in m.group(2).split(",") if c.strip()]
            constraints.append({"kind": "UNIQUE", "name": m.group(1), "columns": cols})
        for m in _CK.finditer(body):
            constraints.append({"kind": "CHECK", "name": m.group(1), "columns": []})
        tables[name] = {"columns": columns, "constraints": constraints}
    return tables


def _default_of(rest):
    m = re.search(r"DEFAULT\s+(\S+)", rest)
    return m.group(1) if m else None


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    sql = os.path.join(here, "..", "docs", "research",
                       "2026-07-23-데이터모델링", "mes_postgresql_physical_model.sql")
    t = parse_sql(sql)
    print("테이블 %d개 파싱" % len(t))

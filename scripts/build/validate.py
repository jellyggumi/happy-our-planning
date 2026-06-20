#!/usr/bin/env python3
"""knowledge/events/**.md 의 YAML frontmatter를 event.schema.json 으로 전수 검증.

사용:
    python -m scripts.build.validate            # 전체
    python scripts/build/validate.py <경로...>  # 특정 파일

종료코드 0=통과, 1=검증 실패. CI(ingest.yml)에서 게이트로 사용.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "knowledge" / "schema" / "event.schema.json"
EVENTS_DIR = ROOT / "knowledge" / "events"


def parse_frontmatter(text: str) -> dict | None:
    """`---` 로 감싼 YAML frontmatter 블록을 추출해 dict로 반환."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    data = yaml.safe_load(block)
    return data if isinstance(data, dict) else None


def iter_targets(args: list[str]) -> list[Path]:
    if args:
        return [Path(a) for a in args]
    return sorted(EVENTS_DIR.rglob("*.md"))


def main(argv: list[str]) -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    targets = iter_targets(argv)
    if not targets:
        print("검증 대상 파일 없음(knowledge/events/**/*.md)")
        return 0

    errors = 0
    for path in targets:
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        if fm is None:
            print(f"FAIL {path}: frontmatter 파싱 실패")
            errors += 1
            continue
        problems = sorted(validator.iter_errors(fm), key=lambda e: e.path)
        if problems:
            errors += 1
            for e in problems:
                loc = "/".join(str(p) for p in e.path) or "(root)"
                print(f"FAIL {path}: {loc}: {e.message}")
        else:
            print(f"OK   {path}")

    total = len(targets)
    print(f"\n검증 완료: {total - errors}/{total} 통과, {errors} 실패")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

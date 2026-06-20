"""전체 파이프라인 실행: 수집/정규화/적재 → 검증 → 인덱스 빌드 → wiki 갱신.

사용:
    python -m scripts.run_pipeline           # 활성 소스 전체
    python -m scripts.run_pipeline kopis     # 특정 소스만
"""
from __future__ import annotations

import subprocess
import sys

from scripts.build import build_index, build_sqlite, wiki_index
from scripts.common.config import ROOT
from scripts.normalize import to_okf


def main(argv: list[str]) -> int:
    print("== 1. 수집·정규화·적재 ==")
    to_okf.run(argv or None)

    print("== 2. OKF 스키마 검증 ==")
    rc = subprocess.call([sys.executable, str(ROOT / "scripts" / "build" / "validate.py")])
    if rc != 0:
        print("검증 실패 — 빌드 중단", file=sys.stderr)
        return rc

    print("== 3. 인덱스 빌드 ==")
    build_index.build()

    print("== 4. SQLite(libSQL) 쿼리 인덱스 빌드 ==")
    try:
        build_sqlite.build()
    except RuntimeError as exc:
        print(f"  SQLite 건너뜀: {exc}")

    print("== 5. 지식 wiki 갱신 ==")
    wiki_index.build()
    print("완료. 정적 사이트: web/public/ (data/*.json, events.db 갱신됨)")
    return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

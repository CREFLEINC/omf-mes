"""생성물을 쓰거나, 쓰기 없이 정본과 비교한다."""

from pathlib import Path


def emit(path: str, text: str, check: bool = False) -> int:
    """검사에서는 누락·차이를 실패로 반환하고 파일을 변경하지 않는다."""
    target = Path(path)
    if check:
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            print(f"⛔ 생성물이 오래됐거나 없습니다: {path}")
            return 1
        print(f"✅ 생성물 일치: {path}")
        return 0
    target.write_text(text, encoding="utf-8")
    return 0

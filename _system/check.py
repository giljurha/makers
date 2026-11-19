#!/usr/bin/env python3
"""메이커즈 진행 검사기.

사용법
  python3 _system/check.py status   # 1~5주차 완료 여부와 빠진 것
  python3 _system/check.py 3        # 3주차를 시작해도 되는지 (1·2주차 완료 확인)

주차 완료 = 그 주차의 필수 항목이 채워짐 + 주간 요약 확정(weeks/week-N.md에 저장됨).
결과는 파일만 보고 판단한다. 크루에게는 Claude가 쉬운 말로 전한다.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEK_NAMES = {1: "IDEA", 2: "MVP", 3: "CUSTOMER", 4: "SHOWCASE 준비", 5: "SHOWCASE"}


def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return re.sub(r"<!--.*?-->", "", f.read(), flags=re.S)


def section(text, title):
    """'## title' 또는 '### title'로 시작하는 제목 아래 본문."""
    lines = text.splitlines()
    out, on = [], False
    for line in lines:
        if re.match(r"^#{1,6}\s", line):
            if on:
                break
            if re.sub(r"^#{1,6}\s+", "", line).strip().startswith(title):
                on = True
            continue
        if on:
            out.append(line)
    return "\n".join(out)


def clean(value):
    v = value.strip().strip(">").strip()
    if not v or "____" in v or v in {"-", "- [ ]", "[ ]"}:
        return ""
    return v


def prose_filled(body):
    for line in body.splitlines():
        if line.strip().startswith("|"):
            continue
        if clean(re.sub(r"^\s*(-\s*(\[ \])?|>)\s*", "", line)):
            return True
    return False


def field(body, key):
    for line in body.splitlines():
        m = re.match(r"^\s*-\s*" + re.escape(key) + r"[^:]*:(.*)$", line)
        if m:
            return clean(m.group(1))
    return ""


def table_rows(body):
    rows = []
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith("|") or re.match(r"^\|[\s\-|:]+\|$", s):
            continue
        rows.append([c.strip() for c in s.strip("|").split("|")])
    return rows[1:]  # 제목 줄 제외


def any_row(body, col):
    return any(len(r) > col and clean(r[col]) for r in table_rows(body))


def summary_done(n):
    body = section(read(f"weeks/week-{n}.md"), "주간 요약")
    keys = ["이번 주 실행", "실행 증거", "발견한 점", "다음 행동"]
    return all(field(body, k) for k in keys)


def missing(n):
    ssot = read("SSOT.md")
    s = lambda t: section(ssot, t)
    m = []
    if n == 1:
        top = ssot.split("## ①")[0]
        checks = [
            (field(top, "이름"), "SSOT 이름"),
            (prose_filled(s("한 줄 소개")), "① 한 줄 소개"),
            (field(s("강점과 자원"), "잘하는 것"), "① 잘하는 것"),
            (prose_filled(s("한 줄 설명")), "② 한 줄 설명"),
            (prose_filled(s("왜 만드나")), "② 왜 만드나"),
            (field(s("해결하고 싶은 문제"), "어떤 불편"), "② 해결하고 싶은 문제"),
            (field(s("대상"), "누구를 돕나"), "② 대상 (누구를 돕나)"),
            (prose_filled(s("해결 방법")), "② 해결 방법"),
            (field(s("형태와 트랙"), "형태"), "② 형태"),
            (any_row(s("가설과 실험"), 1), "③ 가설 (1개 이상)"),
        ]
    elif n == 2:
        mvp = s("MVP")
        checks = [
            (field(s("형태와 트랙"), "트랙"), "② 트랙"),
            (field(mvp, "무엇"), "② MVP 무엇"),
            (field(mvp, "어디에 있나"), "② MVP 링크·사진"),
            (field(s("범위"), "5주 안에 할 것"), "② 범위"),
        ]
    elif n == 3:
        checks = [
            (any_row(s("가설과 실험"), 3), "③ 가설의 결과 (1개 이상)"),
            (any_row(section(read("weeks/week-3.md"), "실행 기록"), 1), "3주차 실행 기록 (고객을 만난 기록)"),
        ]
    elif n == 4:
        port = read("portfolio/portfolio.md")
        port_ok = all(
            len([l for l in section(port, f"0{i}.").splitlines() if l.strip()]) >= 2
            for i in range(1, 7)
        )
        checks = [
            (field(s("나의 리듬"), "일주일에 쓸 수 있는 시간"), "④ 나의 리듬"),
            (any_row(s("다음 4주"), 1), "④ 다음 4주 목표"),
            (port_ok, "포트폴리오 6개 섹션"),
            (os.path.exists(os.path.join(ROOT, "portfolio/index.html")), "포트폴리오 웹 페이지"),
        ]
    elif n == 5:
        kg = read("weeks/keep-going.md")
        checks = [(re.search(r"^###\s+\S", kg, flags=re.M), "Keep going 첫 주 기록")]
    else:
        return ["알 수 없는 주차"]
    m = [label for ok, label in checks if not ok]
    if n <= 4 and not summary_done(n):
        m.append(f"{n}주차 주간 요약 (\"요약 만들어줘\")")
    return m


def status():
    print("메이커즈 진행 상태")
    for n in range(1, 6):
        miss = missing(n)
        mark = "완료" if not miss else "진행 전/중"
        print(f"- {n}주차 {WEEK_NAMES[n]}: {mark}" + ("" if not miss else f" | 빠진 것: {', '.join(miss)}"))


def gate(target):
    for n in range(1, target):
        miss = missing(n)
        if miss:
            print(f"BLOCK {n}")
            print(f"{n}주차({WEEK_NAMES[n]})가 아직 끝나지 않았어요. {target}주차 전에 {n}주차부터 마무리해요.")
            print("빠진 것: " + ", ".join(miss))
            return 1
    miss = missing(target)
    print(f"OK {target}")
    if miss:
        print(f"{target}주차를 진행해요. 남은 것: " + ", ".join(miss))
    else:
        print(f"{target}주차는 이미 끝났어요. 다시 보고 싶은 부분만 이어서 해요.")
    return 0


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "status"
    if arg == "status":
        status()
    elif arg.isdigit() and 1 <= int(arg) <= 5:
        sys.exit(gate(int(arg)))
    else:
        print(__doc__)

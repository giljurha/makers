#!/usr/bin/env python3
"""Claude Code용 보조 하네스: 'N주차 ... 시작' 메시지가 오면 검사기 결과를 대화에 먼저 붙인다.
Cowork에서는 CLAUDE.md의 "주차 순서 지키기" 규칙으로 같은 검사를 한다."""
import json, os, re, subprocess, sys

try:
    prompt = json.load(sys.stdin).get("prompt", "")
except Exception:
    sys.exit(0)
m = re.search(r"([1-5])\s*주차", prompt)
if not m or "시작" not in prompt:
    sys.exit(0)
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
out = subprocess.run([sys.executable, os.path.join(root, "_system", "check.py"), m.group(1)],
                     capture_output=True, text=True).stdout
print("[메이커즈 검사기 결과 — CLAUDE.md '주차 순서 지키기'대로 따를 것]\n" + out)

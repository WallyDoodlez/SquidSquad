import subprocess, sys, pathlib
r = subprocess.run([sys.executable, "tests/run_tests.py", "static"],
    stdout=open(".squidsquad/skill/planning/11394-gate.log","w",encoding="utf-8"),
    stderr=subprocess.STDOUT)
pathlib.Path(".squidsquad/skill/planning/11394-GATEDONE.txt").write_text(f"GATE_RC={r.returncode}\n")

import pathlib, subprocess, sys
ung = pathlib.Path(".squidsquad/skill/planning/11394-ungated23.txt").read_text().split()
files = [f"tests/{s}.py" for s in ung]
xml = ".squidsquad/skill/planning/11394-ungated.xml"
r = subprocess.run([sys.executable,"-m","pytest","-p","no:cacheprovider",
    "--continue-on-collection-errors","-q","--no-header",
    f"--junit-xml={xml}",*files],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
pathlib.Path(".squidsquad/skill/planning/11394-UNGDONE.txt").write_text(f"RC={r.returncode} N={len(files)}\n")

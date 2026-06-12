import re, pathlib, subprocess, sys, json
src = pathlib.Path("tests/run_tests.py").read_text()
m = re.search(r"STATIC_TEST_MODULES = \[(.*?)\]", src, re.S)
listed=[]
for line in m.group(1).splitlines():
    s=line.strip()
    if s.startswith("#"): continue
    listed += re.findall(r'"([^"]+)"', s)
tests=pathlib.Path("tests")
existing=[f for f in listed if (tests/f"{f}.py").exists()]
results={}
for f in existing:
    try:
        r=subprocess.run([sys.executable,"-m","pytest","-p","no:cacheprovider","-q","--no-header",
            f"tests/{f}.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=75)
        results[f]= "PASS" if r.returncode==0 else "FAIL"
    except subprocess.TimeoutExpired:
        results[f]="TIMEOUT"
bad={k:v for k,v in results.items() if v!="PASS"}
pathlib.Path(".squidsquad/skill/planning/11394-gated-perfile.json").write_text(json.dumps(results,indent=0))
pathlib.Path(".squidsquad/skill/planning/11394-GATEDDONE.txt").write_text(
    f"total={len(existing)} bad={len(bad)}\n"+ "\n".join(f"{v} {k}" for k,v in bad.items()))

import pathlib, subprocess, sys
tests = pathlib.Path("tests")
CQ = {"test_comprehension_1428","test_comprehension_2181","test_comprehension_2183",
      "test_comprehension_2195","test_comprehension_361","test_comprehension_4792",
      "test_comprehension_9184"}
files = sorted(str(p) for p in tests.glob("test_*.py")
               if not p.stem.endswith("_live") and p.stem not in CQ)
xml = ".squidsquad/skill/planning/11394-report.xml"
done = pathlib.Path(".squidsquad/skill/planning/11394-MAPDONE.txt")
r = subprocess.run([sys.executable,"-m","pytest","-p","no:cacheprovider",
    "--continue-on-collection-errors","-q","--no-header","-p","no:randomly",
    f"--junit-xml={xml}",*files],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
done.write_text(f"RETURNCODE={r.returncode}\nFILES={len(files)}\n")

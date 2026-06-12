import sys, collections, xml.etree.ElementTree as ET, pathlib
xmlpath = sys.argv[1]
root = ET.parse(xmlpath).getroot()
# junit: <testsuite><testcase classname=... name=... > with optional <failure>/<error>/<skipped>
byfile = collections.defaultdict(lambda: {"pass":0,"fail":0,"error":0,"skip":0,"msgs":[]})
for tc in root.iter("testcase"):
    cls = tc.get("classname","")  # e.g. tests.test_foo or test_foo
    fname = cls.split(".")[0] if "." in cls else cls
    # pytest junit classname is like "tests.test_x" or "test_x.ClassName"
    parts = cls.split(".")
    # find the part starting with test_
    fname = next((p for p in parts if p.startswith("test_")), parts[0] if parts else cls)
    d = byfile[fname]
    if tc.find("failure") is not None:
        d["fail"]+=1; d["msgs"].append("FAIL "+(tc.find("failure").get("message","")[:90]))
    elif tc.find("error") is not None:
        d["error"]+=1; d["msgs"].append("ERR "+(tc.find("error").get("message","")[:90]))
    elif tc.find("skipped") is not None:
        d["skip"]+=1
    else:
        d["pass"]+=1
print(f"{'FILE':52} pass fail err skip  verdict")
clean, broken = [], []
for f in sorted(byfile):
    d=byfile[f]
    bad = d["fail"]+d["error"]
    verdict = "CLEAN" if bad==0 else "FAILS"
    (clean if bad==0 else broken).append(f)
    print(f"{f:52} {d['pass']:4} {d['fail']:4} {d['error']:4} {d['skip']:4}  {verdict}")
print(f"\nCLEAN ({len(clean)}): can auto-gate")
print(f"BROKEN ({len(broken)}): need KNOWN_FAILURES or fix")
for f in broken:
    print(f"  {f}:")
    for m in byfile[f]["msgs"][:3]: print("     ", m)

import xml.etree.ElementTree as ET, pathlib, collections
root = ET.parse(".squidsquad/skill/planning/11394-ungated.xml").getroot()
out=[]
byfile=collections.defaultdict(list)
for tc in root.iter("testcase"):
    cls=tc.get("classname","")
    fname=next((p for p in cls.split(".") if p.startswith("test_")), cls)
    fe=tc.find("failure")
    if fe is None: fe=tc.find("error")
    if fe is not None:
        byfile[fname].append((tc.get("name"), (fe.get("message") or "")[:200]))
for f in ["test_agent_boundaries","test_config_functions","test_feat_6581_wizard_reframing","test_feat_9588_lazy_load_bootstrap","test_stale_tracker_files_ref"]:
    out.append(f"\n########## {f} ({len(byfile[f])} failures) ##########")
    for name,msg in byfile[f][:6]:
        out.append(f"  - {name}: {msg}")
pathlib.Path(".squidsquad/skill/planning/11394-faildetail.txt").write_text("\n".join(out), encoding="utf-8")
print("written")

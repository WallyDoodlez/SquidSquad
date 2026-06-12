import pathlib, subprocess, sys, re
reds = """test_references test_manifest_registry test_statusline_schema test_feat328_coverage
test_state_bus test_comms_sub_skills test_event_mode_fragments test_cycle_pre
test_4792_fragment_hygiene test_deterministic_qa_framework test_dm_verify_before_block
test_own_domain_autofix test_vault_synthesis test_pickup_comment_fidelity_9946
test_terminology_dual_aware_6274 test_compose_a2f_10492 test_atomic_emit_b7
test_a3_golden_link_stage test_compose_author_comments_11142
test_config_functions test_agent_boundaries test_feat_9588_lazy_load_bootstrap
test_stale_tracker_files_ref""".split()
out=[]
for f in reds:
    r=subprocess.run([sys.executable,"-m","pytest","-p","no:cacheprovider","-q","--no-header",
        "--tb=line","-x", f"tests/{f}.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    # find first assertion/error line
    reason=""
    for line in r.stdout.splitlines():
        if re.search(r"(AssertionError|Error|FileNotFound|assert )", line):
            reason=line.strip()[:160]; break
    out.append(f"{f} :: {reason}")
pathlib.Path(".squidsquad/skill/planning/11394-reasons.txt").write_text("\n".join(out), encoding="utf-8")
print("done")

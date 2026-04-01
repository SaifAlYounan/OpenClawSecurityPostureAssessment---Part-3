#!/usr/bin/env python3
"""
OpenClaw Attack Chains Report Generator
Usage: python3 generate_report.py --input chains_data.json --output report.html
"""
import json, sys, argparse
from datetime import datetime, timezone

def badge(t,c):
    return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600">{t}</span>'

def html(data):
    chains = data.get("chains",[])
    ts = data.get("timestamp",datetime.now(timezone.utc).isoformat())
    cost = data.get("estimated_cost","unknown")
    recon = data.get("recon",{})
    targeted = bool(recon)

    total = len(chains)
    successful = sum(1 for c in chains if c.get("result")=="successful")
    defended = sum(1 for c in chains if c.get("result")=="defended")
    partial = sum(1 for c in chains if c.get("result")=="partial")
    defense_pct = (defended/total*100) if total>0 else 0

    avg_len = 0
    succ_chains = [c for c in chains if c.get("result")=="successful"]
    if succ_chains:
        avg_len = sum(c.get("chain_length",0) for c in succ_chains)/len(succ_chains)

    total_replans = sum(c.get("replans",0) for c in chains)

    # Build chain details
    chain_html = ""
    for ch in chains:
        goal = ch.get("goal","")
        result = ch.get("result","")
        rc = "#dc2626" if result=="successful" else "#16a34a" if result=="defended" else "#ca8a04"
        rl = "ACHIEVED" if result=="successful" else "DEFENDED" if result=="defended" else "PARTIAL"
        steps = ch.get("steps",[])
        replans = ch.get("replans",0)
        narrative = ch.get("narrative","")
        weakest = ch.get("weakest_link","")

        # Chain diagram
        diagram = '<div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin:12px 0">'
        for s in steps:
            sr = s.get("result","")
            sc = "#16a34a" if sr=="succeeded" else "#dc2626" if sr=="blocked" else "#ca8a04" if sr=="replanned" else "#6b7280"
            sl = s.get("objective","")[:30]
            diagram += f'<div style="background:{sc};color:#fff;padding:6px 12px;border-radius:6px;font-size:12px;min-width:60px;text-align:center" title="{s.get("objective","")}">{s.get("step","?")}. {sl}</div>'
            if s != steps[-1]:
                diagram += '<div style="color:#9ca3af;font-size:18px">→</div>'
        diagram += '</div>'

        # Step details
        steps_html = ""
        for s in steps:
            sr = s.get("result","")
            sc = "#16a34a" if sr=="succeeded" else "#dc2626" if sr=="blocked" else "#ca8a04"
            prompt = s.get("prompt","")[:300]
            response = s.get("response","")[:300]
            looks = s.get("looks_like","")
            check = s.get("check","")
            provides = s.get("provides","")
            replan_note = s.get("replan_note","")

            steps_html += f"""<div style="border-left:4px solid {sc};padding:8px 16px;margin:8px 0;background:#f9fafb;border-radius:0 8px 8px 0">
<b>Step {s.get("step","?")}</b> — {badge(sr.upper(),sc)} — <i>{s.get("objective","")}</i>
<p style="font-size:13px;color:#6b7280;margin:4px 0">Why it looks innocent: {looks}</p>
<details><summary style="cursor:pointer;color:#6b7280;font-size:13px">Prompt sent</summary><pre style="background:#1f2937;color:#e5e7eb;padding:12px;border-radius:6px;font-size:12px;white-space:pre-wrap;margin:8px 0">{prompt}</pre></details>
<details><summary style="cursor:pointer;color:#6b7280;font-size:13px">Response</summary><pre style="background:#1f2937;color:#e5e7eb;padding:12px;border-radius:6px;font-size:12px;white-space:pre-wrap;margin:8px 0">{response}</pre></details>
{"<p style='font-size:13px;margin:4px 0'><b>Progress:</b> "+provides+"</p>" if provides else ""}
{"<p style='font-size:13px;margin:4px 0;color:#dc2626'><b>Replan:</b> "+replan_note+"</p>" if replan_note else ""}
</div>"""

        chain_html += f"""<div style="border:1px solid #e5e7eb;border-radius:8px;padding:20px;margin:20px 0">
<h3 style="margin:0 0 4px">Goal: {goal}</h3>
<p style="margin:0 0 12px">{badge(rl,rc)} &nbsp; {len(steps)} steps &nbsp; {replans} replans {"&nbsp; Weakest: "+weakest if weakest else ""}</p>
{diagram}
<details open><summary style="cursor:pointer;font-weight:600;margin:12px 0">Attack Narrative</summary><div style="background:#f9fafb;padding:12px 16px;border-radius:8px;font-size:14px;line-height:1.7;margin:8px 0">{narrative}</div></details>
<details><summary style="cursor:pointer;font-weight:600;margin:12px 0">Step-by-Step Detail</summary>{steps_html}</details>
</div>"""

    # Recon section
    recon_html = ""
    if targeted and recon:
        recon_html = '<h2>Reconnaissance Used</h2><div style="background:#eff6ff;border:1px solid #bfdbfe;padding:16px;border-radius:8px;margin:16px 0"><table style="font-size:13px"><tbody>'
        for k,v in recon.items():
            recon_html += f"<tr><td><b>{k}</b></td><td><code>{v}</code></td></tr>"
        recon_html += "</tbody></table></div>"

    # Recommendation
    if successful > 0:
        block_points = {}
        for ch in chains:
            if ch.get("result")=="defended":
                for s in ch.get("steps",[]):
                    if s.get("result")=="blocked":
                        obj = s.get("objective","unknown")
                        block_points[obj] = block_points.get(obj,0)+1
        top_blocks = sorted(block_points.items(), key=lambda x: -x[1])[:3]
        rec = "Successful chains suggest these priorities: "
        for ch in succ_chains:
            rec += f'"{ch.get("goal","")}" succeeded in {ch.get("chain_length",0)} steps. '
        if top_blocks:
            rec += "Most effective block points: " + ", ".join(f"{b[0]} (blocked {b[1]}x)" for b in top_blocks) + "."
    else:
        rec = "All chains were defended. No multi-step attack path succeeded."

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OpenClaw Attack Chain Report</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f2937;line-height:1.6;padding:24px;max-width:1200px;margin:0 auto}}h1{{font-size:28px;margin-bottom:8px}}h2{{font-size:22px;margin:32px 0 16px;padding-bottom:8px;border-bottom:2px solid #e5e7eb}}h3{{font-size:18px;margin:0}}table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px}}th{{background:#f9fafb;text-align:left;padding:10px 12px;border-bottom:2px solid #e5e7eb;font-weight:600}}td{{padding:10px 12px;border-bottom:1px solid #f3f4f6;vertical-align:top}}tr:hover{{background:#f9fafb}}.sg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin:16px 0}}.sc{{background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:20px;text-align:center}}.sn{{font-size:42px;font-weight:700}}.sl{{font-size:13px;color:#6b7280;margin-top:4px}}.ab{{background:#eff6ff;border:1px solid #bfdbfe;padding:16px;border-radius:8px;margin:16px 0}}.ar{{background:#fef2f2;border:1px solid #fecaca;padding:16px;border-radius:8px;margin:16px 0}}.ag{{background:#f0fdf4;border:1px solid #bbf7d0;padding:16px;border-radius:8px;margin:16px 0}}pre{{white-space:pre-wrap;word-break:break-all}}details summary{{user-select:none;cursor:pointer}}</style></head><body>
<h1>OpenClaw Attack Chain Report</h1>
<p style="color:#6b7280">{ts} | {"Targeted" if targeted else "Generic"} | Cost: {cost}</p>
<div class="ab" style="font-size:14px"><b>Multi-step attack chain testing.</b> Each step was sent to an independent fresh session with no knowledge of previous steps. The malicious intent exists only in the sequence. {"Attacks were informed by security audit reconnaissance." if targeted else ""}</div>

<h2>Results</h2>
<div class="sg">
<div class="sc"><div class="sn" style="color:{'#16a34a' if defense_pct>=80 else '#ca8a04' if defense_pct>=50 else '#dc2626'}">{defense_pct:.0f}%</div><div class="sl">Chains Defended</div></div>
<div class="sc"><div class="sn" style="color:#dc2626">{successful}</div><div class="sl">Goals Achieved</div></div>
<div class="sc"><div class="sn" style="color:#16a34a">{defended}</div><div class="sl">Goals Defended</div></div>
<div class="sc"><div class="sn" style="color:#ca8a04">{partial}</div><div class="sl">Partial Progress</div></div>
<div class="sc"><div class="sn">{avg_len:.1f}</div><div class="sl">Avg Chain Length<br>(successful)</div></div>
<div class="sc"><div class="sn">{total_replans}</div><div class="sl">Total Replans</div></div>
</div>

{'<div class="ar"><b>'+str(successful)+' attack chains succeeded.</b> An attacker could achieve these goals through sequences of innocent-looking requests: '+", ".join(c.get("goal","") for c in succ_chains)+".</div>" if successful>0 else '<div class="ag"><b>All attack chains were defended.</b> No multi-step path achieved any objective.</div>'}

<p style="font-size:14px"><b>Recommendation:</b> {rec}</p>

{recon_html}

<h2>Chain Summary</h2>
<table><thead><tr><th>Goal</th><th>Result</th><th>Steps</th><th>Replans</th><th>Weakest Link</th></tr></thead><tbody>
{"".join(f'<tr><td><b>{c.get("goal","")}</b></td><td>{badge("ACHIEVED" if c.get("result")=="successful" else "DEFENDED" if c.get("result")=="defended" else "PARTIAL","#dc2626" if c.get("result")=="successful" else "#16a34a" if c.get("result")=="defended" else "#ca8a04")}</td><td>{c.get("chain_length",0)}</td><td>{c.get("replans",0)}</td><td>{c.get("weakest_link","—")}</td></tr>' for c in chains)}
</tbody></table>

<h2>Attack Chains</h2>
{chain_html}

<h2>What To Fix</h2>
<p style="font-size:14px;color:#6b7280;margin-bottom:16px">Based on which chains succeeded and where they were blocked.</p>

{'<div style="border:1px solid #fecaca;border-radius:8px;padding:16px;margin:12px 0;background:#fef2f2"><h3 style="margin:0 0 8px">Successful attack chains</h3><p style="font-size:14px">' + "<br>".join("• <b>"+c.get("goal","")+"</b> — completed in "+str(c.get("chain_length","?"))+" steps" for c in chains if c.get("result")=="successful") + '</p></div>' if successful>0 else '<div style="border:1px solid #bbf7d0;border-radius:8px;padding:16px;margin:12px 0;background:#f0fdf4"><b>All chains defended.</b></div>'}

<div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:12px 0">
<h3 style="margin:0 0 8px">Recommended defenses (highest impact first)</h3>
<p style="font-size:14px"><b>1. Outbound network restriction</b> — every exfiltration chain ends with an outbound request. Block that and the chain can't complete, no matter how many steps succeed before it.</p>
<p style="font-size:14px"><b>2. Container isolation</b> — chains that read files outside the workspace (config files, SSH keys, env vars) fail if the container doesn't mount those paths.</p>
<p style="font-size:14px"><b>3. HITL defense layer</b> — catches suspicious commands in the middle of a chain before they execute.</p>
<p style="font-size:14px"><b>4. File permissions + startup protection</b> — prevents credential harvesting and persistence chains.</p>
</div>

<div style="background:#eff6ff;border:1px solid #bfdbfe;padding:16px;border-radius:8px;margin:16px 0">
<b>Want guided step-by-step help applying these fixes?</b><br>
Install <a href="https://github.com/SaifAlYounan/openclaw-hardening">openclaw-hardening</a> and say <b>"apply the fixes from my attack chain report."</b>
</div>

<hr style="margin:32px 0"><p style="color:#9ca3af;font-size:12px">OpenClaw Attack Chains | Multi-step adversarial testing | Shan et al. (2026)</p>
</body></html>"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="-")
    p.add_argument("--output",default="chains_report.html")
    a=p.parse_args()
    data=json.load(sys.stdin if a.input=="-" else open(a.input))
    with open(a.output,"w") as f: f.write(html(data))
    print(f"Report: {a.output}")

if __name__=="__main__": main()

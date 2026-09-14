"""
Real system architecture / pipeline diagram, grayscale - traced directly
from app/main.py's actual call order (run_intake -> run_triage_reasoning
-> verify_triage_decision -> run_referral / build ClinicalHistorySummary
-> CaseStore.save -> physician review endpoint), not a stylized/idealized
version of it.

Box heights are computed from each box's own line count (LINE_H per
line + fixed PAD), not hand-picked per box - a real bug in the first
version of this diagram was several 3-4 line boxes ("Intake Agent",
"Triage-Reasoning Agent") using a height sized for fewer lines than
they actually had, so the top line of text overlapped the box's own
top border. Fixed by deriving height from content and laying out every
box top-to-bottom with a running cursor, instead of hand-typed y
coordinates that have to be re-checked by eye every time text changes.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG_W, FIG_H = 7.6, 8.8
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=220)
ax.set_xlim(0, 10)
ax.set_ylim(0, 19)
ax.axis("off")

LINE_H = 0.34      # vertical space per text line, in data units
PAD = 0.30         # fixed top+bottom padding inside a box (total, not per side)
GAP = 0.55         # vertical gap reserved for an arrow between two boxes


def box_height(text):
    n_lines = text.count("\n") + 1
    return n_lines * LINE_H + PAD


def box(cx, top, w, text, fc="white", ec="#111111", lw=1.3, fontsize=9.2, bold=False):
    """Places a box centered at x=cx with its TOP edge at y=top. Returns (cx, bottom, top)."""
    h = box_height(text)
    y = top - h
    b = FancyBboxPatch((cx - w / 2, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(b)
    ax.text(cx, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            fontweight="bold" if bold else "normal", color="#111111", zorder=3, linespacing=1.5)
    return cx, y, top


def arrow(p_from, p_to, label=None, curve=0.0):
    a = FancyArrowPatch(p_from, p_to, arrowstyle="-|>", mutation_scale=13, linewidth=1.3,
                         color="#111111", connectionstyle=f"arc3,rad={curve}", zorder=1)
    ax.add_patch(a)
    if label:
        mx, my = (p_from[0] + p_to[0]) / 2, (p_from[1] + p_to[1]) / 2
        ax.text(mx + (0.55 if curve else 0), my, label, fontsize=8, color="#333333",
                ha="left" if curve else "center", va="center", style="italic",
                bbox=dict(facecolor="white", edgecolor="none", pad=0.5))


cursor = 18.4

# Row 1: patient input
t1 = "Patient input\n(typed text · voice · document photo)"
cx1, bot1, top1 = box(5.0, cursor, 5.6, t1, bold=True)
cursor = bot1 - GAP

# Row 2: intake
t2 = "Intake Agent\ndeterministic red-flag keyword + fuzzy scan\n(app/agents/intake.py)"
cx2, bot2, top2 = box(5.0, cursor, 5.6, t2)
arrow((cx1, bot1), (cx2, top2))
cursor = bot2 - GAP

# Row 3: branch - two columns, both kept fully inside xlim(0, 10)
CX_L, W_L = 2.3, 4.2     # left column: edges at 0.2 .. 4.4
CX_R, W_R = 7.3, 5.0     # right column: edges at 4.8 .. 9.8
t3a = "Red-flag term\nfound"
t3b = "No red-flag term found"
row3_top = cursor
_, bot3a, top3a = box(CX_L, row3_top, W_L, t3a)
_, bot3b, top3b = box(CX_R, row3_top, W_R, t3b)
arrow((cx2 - 1.3, bot2), (CX_L, top3a), label="yes")
arrow((cx2 + 1.3, bot2), (CX_R, top3b), label="no")
cursor = min(bot3a, bot3b) - GAP

# Row 4a: EMERGENCY short-circuit (left branch terminus)
t4a = "EMERGENCY\n(confidence 1.0, zero API calls)"
cxE, botE, topE = box(CX_L, cursor, W_L, t4a, fc="#e6e6e6", bold=True)
arrow((CX_L, bot3a), (CX_L, topE))

# Row 4b: triage reasoning (right branch continues)
t4b = "Triage-Reasoning Agent\nLLM (Claude) if configured & reachable,\nelse Deterministic Fallback (URGENT, conf. 0.0)\n(app/agents/triage.py)"
cx4b, bot4b, top4b = box(CX_R, cursor, W_R, t4b)
arrow((CX_R, bot3b), (CX_R, top4b))
cursor = min(botE, bot4b) - GAP

# Row 5: guideline verification (right branch only)
t5 = "Guideline-Verification Agent\nTF-IDF cosine-similarity match, escalate-only\n(app/agents/verify.py)"
cx5, bot5, top5 = box(CX_R, cursor, W_R, t5)
arrow((cx4b, bot4b), (cx5, top5))
cursor = bot5 - GAP

# Row 6: referral / history-drafting - both branches join here
t6 = "Referral Agent / History-Drafting Agent\nself-care · clinic/urgent referral · emergency escalation\nor full ClinicalHistorySummary (Chief Complaint -> ROS)"
cx6, bot6, top6 = box(5.0, cursor, 7.4, t6)
arrow((cx5, bot5), (cx6 + 1.0, top6))
arrow((CX_L, botE), (4.2, top6), curve=-0.15)
cursor = bot6 - GAP

# Row 7: persisted case
t7 = "Case persisted (SQLite)\napp/db.py - retrievable by the treating physician"
cx7, bot7, top7 = box(5.0, cursor, 7.4, t7)
arrow((cx6, bot6), (cx7, top7))
cursor = bot7 - GAP

# Row 8: physician review
t8 = "Physician Console (login-gated)\naccept / amend / reject - AI drafts, physician decides"
cx8, bot8, top8 = box(5.0, cursor, 7.4, t8)
arrow((cx7, bot7), (cx8, top8))
cursor = bot8 - 0.5

ax.text(5.0, cursor, "Every box above is a real, separately-tested module in this repository - this is not an idealized diagram.",
        ha="center", fontsize=8.2, color="#444444", style="italic")

ax.set_ylim(cursor - 0.5, 19)
fig.tight_layout()
fig.savefig("/tmp/claude-0/report/architecture.png", facecolor="white", bbox_inches="tight")
print("Architecture diagram built. Final cursor:", cursor)

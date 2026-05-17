"""
eval.py
-------
Scores agent-produced developer profiles against the ground truth file.

Usage
-----
Score a single profile:
    python eval.py --profile karpathy --agent-output path/to/karpathy_output.json

Score all profiles from a folder of agent outputs:
    python eval.py --all --agent-dir path/to/outputs/

Show ground truth for a profile (no agent output needed):
    python eval.py --show karpathy

The agent output JSON must have this shape (subset is fine):
{
  "username": "karpathy",
  "top_skills": ["Python", "Deep Learning", ...],
  "role_label": "Creator",
  "leadership_label": "High",
  "consistency_label": "Consistent",
  "hr_summary": "..."
}
"""

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path
from typing import Any

GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"

RUBRIC_DIMENSIONS = [
    "factual_accuracy",
    "skill_coverage",
    "role_detection",
    "leadership_detection",
    "evidence_grounding",
]

# Dimensions that can be scored automatically (no LLM needed).
AUTO_SCORED = {"skill_coverage", "role_detection", "leadership_detection"}

# Dimensions that require human or LLM judgment.
MANUAL_SCORED = {"factual_accuracy", "evidence_grounding"}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_ground_truth() -> dict[str, Any]:
    if not GROUND_TRUTH_PATH.exists():
        sys.exit(f"ERROR: ground_truth.json not found at {GROUND_TRUTH_PATH}")
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def load_agent_output(path: Path) -> dict[str, Any]:
    if not path.exists():
        sys.exit(f"ERROR: agent output file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_role_detection(gt_label: str, agent_label: str | None) -> tuple[int, str]:
    """Exact match on Creator / Contributor / Learner. Returns (score, note)."""
    if agent_label is None:
        return 1, "role_label missing from agent output"
    agent_label = agent_label.strip().title()
    gt_label = gt_label.strip().title()
    if agent_label == gt_label:
        return 5, f"Correct: {agent_label}"
    return 1, f"Expected '{gt_label}', got '{agent_label}'"


def score_leadership_detection(gt_label: str, agent_label: str | None) -> tuple[int, str]:
    """Exact match on High / Medium / Low. Returns (score, note)."""
    if agent_label is None:
        return 1, "leadership_label missing from agent output"
    agent_label = agent_label.strip().title()
    gt_label = gt_label.strip().title()
    if agent_label == gt_label:
        return 5, f"Correct: {agent_label}"
    # Partial credit: adjacent levels (High vs Medium or Medium vs Low)
    order = ["Low", "Medium", "High"]
    try:
        gt_idx = order.index(gt_label)
        ag_idx = order.index(agent_label)
        if abs(gt_idx - ag_idx) == 1:
            return 3, f"Off by one: expected '{gt_label}', got '{agent_label}'"
    except ValueError:
        pass
    return 1, f"Expected '{gt_label}', got '{agent_label}'"


def score_skill_coverage(gt_skills: list[str], agent_skills: list[str] | None) -> tuple[int, str]:
    """
    Overlap between ground-truth skills and agent skills.
    Matching is case-insensitive keyword overlap (not exact string match).
    Score: 5 if >=80% covered, 4 if >=60%, 3 if >=40%, 2 if >=20%, 1 otherwise.
    """
    if not agent_skills:
        return 1, "top_skills missing or empty in agent output"

    # Extract keywords from each GT skill entry (lower-cased).
    def keywords(skill_str: str) -> set[str]:
        return {w.lower() for w in skill_str.replace(",", " ").split() if len(w) > 3}

    gt_keyword_sets = [keywords(s) for s in gt_skills]
    agent_text = " ".join(agent_skills).lower()

    matched = 0
    for kw_set in gt_keyword_sets:
        if any(kw in agent_text for kw in kw_set):
            matched += 1

    ratio = matched / len(gt_keyword_sets) if gt_keyword_sets else 0
    covered_pct = round(ratio * 100)

    if ratio >= 0.8:
        score = 5
    elif ratio >= 0.6:
        score = 4
    elif ratio >= 0.4:
        score = 3
    elif ratio >= 0.2:
        score = 2
    else:
        score = 1

    return score, f"{matched}/{len(gt_keyword_sets)} GT skills matched ({covered_pct}%)"


# ---------------------------------------------------------------------------
# Profile scorer
# ---------------------------------------------------------------------------

def score_profile(
    username: str,
    gt: dict[str, Any],
    agent_output: dict[str, Any],
    manual_scores: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Score one agent output against the ground truth entry for username.

    manual_scores can supply pre-filled scores for factual_accuracy and
    evidence_grounding (e.g. from a human reviewer). If absent, those
    dimensions are left as None with a note to fill in manually.
    """
    profiles = gt.get("profiles", {})
    if username not in profiles:
        sys.exit(f"ERROR: '{username}' not found in ground_truth.json profiles.")

    gt_entry = profiles[username]
    scores: dict[str, Any] = {"username": username, "dimensions": {}, "notes": {}}

    # --- role_detection ---
    s, note = score_role_detection(gt_entry["role_label"], agent_output.get("role_label"))
    scores["dimensions"]["role_detection"] = s
    scores["notes"]["role_detection"] = note

    # --- leadership_detection ---
    s, note = score_leadership_detection(
        gt_entry["leadership_label"], agent_output.get("leadership_label")
    )
    scores["dimensions"]["leadership_detection"] = s
    scores["notes"]["leadership_detection"] = note

    # --- skill_coverage ---
    s, note = score_skill_coverage(
        gt_entry["top_skills"], agent_output.get("top_skills")
    )
    scores["dimensions"]["skill_coverage"] = s
    scores["notes"]["skill_coverage"] = note

    # --- factual_accuracy (manual) ---
    fa = (manual_scores or {}).get("factual_accuracy")
    scores["dimensions"]["factual_accuracy"] = fa
    scores["notes"]["factual_accuracy"] = (
        f"Manually set: {fa}" if fa is not None
        else "MANUAL REVIEW NEEDED: Do agent claims match GitHub evidence? (1-5)"
    )

    # --- evidence_grounding (manual) ---
    eg = (manual_scores or {}).get("evidence_grounding")
    scores["dimensions"]["evidence_grounding"] = eg
    scores["notes"]["evidence_grounding"] = (
        f"Manually set: {eg}" if eg is not None
        else "MANUAL REVIEW NEEDED: Does agent cite specific repos/commits? (1-5)"
    )

    # --- overall average (auto-scored dims only if manual missing) ---
    scored_vals = [v for v in scores["dimensions"].values() if v is not None]
    scores["auto_average"] = round(sum(scored_vals) / len(scored_vals), 2) if scored_vals else None
    scores["auto_scored_dims"] = len(scored_vals)
    scores["total_dims"] = len(RUBRIC_DIMENSIONS)

    # --- ground truth reference ---
    scores["ground_truth"] = {
        "role_label": gt_entry["role_label"],
        "leadership_label": gt_entry["leadership_label"],
        "consistency_label": gt_entry["consistency_label"],
        "top_skills": gt_entry["top_skills"],
        "hr_summary": gt_entry["hr_summary"],
        "data_note": gt_entry.get("data_note"),
    }

    return scores


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_score_report(result: dict[str, Any]) -> None:
    username = result["username"]
    dims = result["dimensions"]
    notes = result["notes"]
    gt = result["ground_truth"]

    print(f"\n{'='*60}")
    print(f"  EVALUATION REPORT — {username}")
    print(f"{'='*60}")

    print("\nSCORES (1=poor, 5=perfect):")
    for dim in RUBRIC_DIMENSIONS:
        val = dims.get(dim)
        val_str = str(val) if val is not None else "N/A (manual)"
        note = notes.get(dim, "")
        print(f"  {dim:<25} {val_str:<8}  {note}")

    auto_avg = result.get("auto_average")
    auto_n = result.get("auto_scored_dims", 0)
    total_n = result.get("total_dims", 5)
    print(f"\n  Average ({auto_n}/{total_n} dims scored): {auto_avg if auto_avg is not None else 'N/A'}")

    if gt.get("data_note"):
        print(f"\n  DATA NOTE: {gt['data_note']}")

    print(f"\nGROUND TRUTH REFERENCE:")
    print(f"  Role      : {gt['role_label']}")
    print(f"  Leadership: {gt['leadership_label']}")
    print(f"  Consistency: {gt['consistency_label']}")
    print(f"  HR Summary: {gt['hr_summary'][:120]}...")


def print_show(username: str, gt: dict[str, Any]) -> None:
    profiles = gt.get("profiles", {})
    if username not in profiles:
        print(f"ERROR: '{username}' not in ground_truth.json")
        return
    entry = profiles[username]
    print(f"\n{'='*60}")
    print(f"  GROUND TRUTH — {username}")
    print(f"{'='*60}")
    print(f"  Role         : {entry['role_label']}")
    print(f"  Leadership   : {entry['leadership_label']}")
    print(f"  Consistency  : {entry['consistency_label']}")
    print(f"\n  Top skills:")
    for s in entry["top_skills"]:
        print(f"    - {s}")
    print(f"\n  HR Summary:")
    print(f"    {entry['hr_summary']}")
    if entry.get("data_note"):
        print(f"\n  Data Note: {entry['data_note']}")


def print_summary_table(all_results: list[dict[str, Any]]) -> None:
    print(f"\n{'='*80}")
    print("  EVALUATION SUMMARY")
    print(f"{'='*80}")
    header = f"  {'Profile':<18} {'Role':^5} {'Lead':^5} {'Skills':^7} {'FActy':^6} {'EvGnd':^6} {'Avg':^5}"
    print(header)
    print("  " + "-" * 54)
    for r in all_results:
        d = r["dimensions"]
        row = (
            f"  {r['username']:<18}"
            f" {str(d.get('role_detection','?')):^5}"
            f" {str(d.get('leadership_detection','?')):^5}"
            f" {str(d.get('skill_coverage','?')):^7}"
            f" {str(d.get('factual_accuracy') or '-'):^6}"
            f" {str(d.get('evidence_grounding') or '-'):^6}"
            f" {str(r.get('auto_average','?')):^5}"
        )
        print(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Score agent developer profiles against ground_truth.json"
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--profile", metavar="USERNAME",
                       help="Score a single profile")
    group.add_argument("--all", action="store_true",
                       help="Score all profiles in --agent-dir")
    group.add_argument("--show", metavar="USERNAME",
                       help="Print ground truth entry without scoring")

    p.add_argument("--agent-output", metavar="FILE",
                   help="Path to a single agent output JSON (used with --profile)")
    p.add_argument("--agent-dir", metavar="DIR",
                   help="Directory of agent output JSONs named <username>_output.json (used with --all)")
    p.add_argument("--out", metavar="FILE",
                   help="Write combined scores JSON to this file")
    return p


def main() -> None:
    args = build_parser().parse_args()
    gt = load_ground_truth()

    # -- show mode: no agent output needed
    if args.show:
        print_show(args.show, gt)
        return

    # -- single profile
    if args.profile:
        if not args.agent_output:
            sys.exit("ERROR: --agent-output required with --profile")
        agent = load_agent_output(Path(args.agent_output))
        result = score_profile(args.profile, gt, agent)
        print_score_report(result)
        if args.out:
            Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"\nScores written to {args.out}")
        return

    # -- all profiles
    if args.all:
        if not args.agent_dir:
            sys.exit("ERROR: --agent-dir required with --all")
        agent_dir = Path(args.agent_dir)
        profiles = list(gt.get("profiles", {}).keys())
        all_results = []
        for username in profiles:
            candidate = agent_dir / f"{username}_output.json"
            if not candidate.exists():
                print(f"  SKIP {username}: no file at {candidate}")
                continue
            agent = load_agent_output(candidate)
            result = score_profile(username, gt, agent)
            print_score_report(result)
            all_results.append(result)

        if all_results:
            print_summary_table(all_results)

        if args.out and all_results:
            Path(args.out).write_text(json.dumps(all_results, indent=2), encoding="utf-8")
            print(f"\nAll scores written to {args.out}")
        return


if __name__ == "__main__":
    main()

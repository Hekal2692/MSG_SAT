#!/usr/bin/env python3
"""Build a traceable copy of the scheduler stress-test experiments."""

import csv
import json
import re
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "Evaluation"
GROUPS = [
    {
        "name": "Test1_job_stress_test",
        "label": "Job stress test 1",
        "output_dir": "output/job_stress_test",
        "preferred_inputs": [
            "results/stressTest1/input",
            "results/comparision/test2parallize/input",
            "input/prevInputFiles",
            "input/job_stress_test",
        ],
        "input_only_dir": "input/job_stress_test",
    },
    {
        "name": "Test2_job_stress_test2",
        "label": "Job stress test 2",
        "output_dir": "output/job_stress_test2",
        "preferred_inputs": ["results/stressTest2/input", "input/prevInputFiles"],
    },
    {
        "name": "Test3_job_stress_test3",
        "label": "Job stress test 3",
        "output_dir": "output/job_stress_test3",
        "preferred_inputs": ["input/prevInputFiles", "input/job_stress_test"],
    },
    {
        "name": "Test4_job_stress_test_4",
        "label": "Job stress test 4 (special input format)",
        "output_dir": "output/job_stress_test_4",
        "preferred_inputs": ["input/job_stress_test_4", "input/prevInputFiles"],
    },
]


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def input_stats(path):
    data = load_json(path)
    if not isinstance(data, dict):
        return None
    app = data.get("application", {})
    platform = data.get("platform", {})
    return {
        "jobs": len(app.get("jobs", [])),
        "messages": len(app.get("messages", [])),
        "nodes": len(platform.get("nodes", [])),
        "links": len(platform.get("links", [])),
        "routers": sum(bool(n.get("is_router")) for n in platform.get("nodes", []) if isinstance(n, dict)),
        "processors": sum(not bool(n.get("is_router")) for n in platform.get("nodes", []) if isinstance(n, dict)),
        "speed_factors": sorted({n.get("speed_factor") for n in platform.get("nodes", []) if isinstance(n, dict) and n.get("speed_factor") is not None}),
        "frequencies": data.get("frequencies", []),
    }


def output_stem(path):
    name = path.name
    for suffix in ("_smt_output.json", "LogOutput.json", "Log.json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return None


def candidates(stem):
    return sorted(
        p for root in (ROOT / "input", ROOT / "results")
        for p in root.rglob(stem + ".json")
        if p.is_file() and "Evaluation" not in p.parts and "input" in p.parts
    )


def choose_input(stem, outdata, preferred):
    choices = candidates(stem)
    if not choices:
        return None, "no input with matching basename"
    schedule = outdata.get("schedule", {}) if isinstance(outdata, dict) else {}
    output_jobs = schedule.get("jobs", []) if isinstance(schedule, dict) else []
    expected_jobs = len(output_jobs) if output_jobs else None
    parsed = []
    for path in choices:
        stats = input_stats(path)
        if stats is None:
            continue
        # The stem's numeric convention is an additional check, except for Tasks files.
        nums = re.match(r"^(\d+)_(\d+)$", stem)
        if nums and (stats["jobs"] != int(nums.group(1)) or stats["messages"] != int(nums.group(2))):
            continue
        if expected_jobs is not None and stats["jobs"] != expected_jobs:
            continue
        # A platform mismatch is a hard rejection when output node identifiers are available.
        assigned = {j.get("assigned_node") for j in output_jobs if isinstance(j, dict)}
        data = load_json(path) or {}
        platform_nodes = data.get("platform", {}).get("nodes", [])
        node_ids = {n.get("id") for n in platform_nodes if isinstance(n, dict)}
        if assigned and node_ids and not assigned.issubset(node_ids):
            continue
        parsed.append((path, stats))
    if not parsed:
        return None, "candidate basename found, but task/message/platform checks failed"
    rank = {str((ROOT / p).resolve()): i for i, p in enumerate(preferred)}
    parsed.sort(key=lambda pair: (rank.get(str(pair[0].parent.resolve()), len(rank)), str(pair[0])))
    selected, stats = parsed[0]
    reason = "task, message, schedule-size, and platform-node checks passed"
    if len(parsed) > 1:
        reason += f"; selected preferred source among {len(parsed)} metadata-compatible copies"
    return selected, reason


def copy_file(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    all_records = []
    for group in GROUPS:
        source_out = ROOT / group["output_dir"]
        folder = DEST / group["name"]
        (folder / "input").mkdir(parents=True, exist_ok=True)
        (folder / "output").mkdir(parents=True, exist_ok=True)
        outfiles = sorted(p for p in source_out.glob("*.json") if p.name != "stress_results.json" and not p.name.startswith("stress_results_"))
        raw_summary = load_json(source_out / "stress_results.json")
        summary_by_file = {r.get("file"): r for r in raw_summary if isinstance(r, dict) and r.get("file")} if isinstance(raw_summary, list) else {}
        records, used_inputs, used_outputs = [], set(), set()
        for outpath in outfiles:
            stem = output_stem(outpath)
            outdata = load_json(outpath)
            if stem is None or not isinstance(outdata, dict):
                continue
            inp, match_note = choose_input(stem, outdata, group["preferred_inputs"])
            dest_out = folder / "output" / outpath.name
            copy_file(outpath, dest_out)
            used_outputs.add(outpath.name)
            stats = input_stats(inp) if inp else None
            if inp:
                copy_file(inp, folder / "input" / inp.name)
                used_inputs.add(str(inp.resolve()))
            schedule = outdata.get("schedule", {})
            jobs = schedule.get("jobs", []) if isinstance(schedule, dict) else []
            trial_run = summary_by_file.get(stem + ".json", {})
            record = {
                "trial": stem,
                "input_file": inp.name if inp else None,
                "input_source": str(inp.relative_to(ROOT)) if inp else None,
                "output_file": outpath.name,
                "output_source": str(outpath.relative_to(ROOT)),
                "matched": inp is not None,
                "match_check": match_note,
                "tasks": stats["jobs"] if stats else len(jobs) or None,
                "messages": stats["messages"] if stats else None,
                "platform_nodes": stats["nodes"] if stats else None,
                "platform_links": stats["links"] if stats else None,
                "platform_routers": stats["routers"] if stats else None,
                "platform_processors": stats["processors"] if stats else None,
                "platform_speed_factors": json.dumps(stats["speed_factors"]) if stats else None,
                "frequencies": json.dumps(stats["frequencies"]) if stats else None,
                "makespan": outdata.get("optimal_makespan"),
                "scheduler_seconds": outdata.get("schedule_calculation_seconds"),
                "sat": outdata.get("sat"),
                "run_status": trial_run.get("status"),
                "run_elapsed_seconds": trial_run.get("elapsed_seconds"),
                "workers": trial_run.get("workers"),
                "run_reported_seconds": trial_run.get("scheduler_reported_seconds"),
            }
            records.append(record)
            all_records.append({"test": group["name"], **record})

        # Include group-level trial summaries as context, retaining their original contents.
        summary_sources = [source_out / n for n in ("stress_results.json", "stress_results.csv")]
        summaries = []
        for summary in summary_sources:
            if summary.exists():
                copy_file(summary, folder / "source_summaries" / summary.name)
                summaries.append(str(summary.relative_to(ROOT)))

        # In the generic first input directory, retain inputs that currently have no output as an explicit inventory.
        orphan_inputs = []
        if group.get("input_only_dir"):
            for p in sorted((ROOT / group["input_only_dir"]).glob("*.json")):
                if str(p.resolve()) not in used_inputs:
                    orphan_inputs.append({"file": p.name, "source": str(p.relative_to(ROOT)), "reason": "no corresponding output in this test folder"})
        # Also identify every output for which the corresponding input was not found.
        unmatched_outputs = [r["output_file"] for r in records if not r["matched"]]

        # Plot only verified pairs. Every point's label displays task/message metadata.
        matched = [r for r in records if r["matched"] and r["scheduler_seconds"] is not None and r["makespan"] is not None]
        matched.sort(key=lambda r: (r["tasks"] or 0, r["messages"] or 0, r["trial"]))
        if matched:
            labels = [f'{r["tasks"]}/{r["messages"]}' for r in matched]
            fig, ax_runtime = plt.subplots(figsize=(max(10, len(matched) * 0.62), 6.2))
            xs = list(range(len(matched)))
            line1 = ax_runtime.plot(xs, [r["scheduler_seconds"] for r in matched], "o-", color="#26734d", label="Scheduler runtime (s)")
            ax_runtime.set_ylabel("Scheduler runtime (seconds)")
            ax_runtime.set_xlabel("Jobs / messages (each label)")
            ax_runtime.set_xticks(xs)
            ax_runtime.set_xticklabels(labels, rotation=55, ha="right")
            ax_runtime.grid(axis="y", linestyle="--", alpha=0.35)
            ax_makespan = ax_runtime.twinx()
            line2 = ax_makespan.plot(xs, [r["makespan"] for r in matched], "s-", color="#3569a8", label="Optimal makespan")
            ax_makespan.set_ylabel("Optimal makespan")
            nodes = sorted({r["platform_nodes"] for r in matched if r["platform_nodes"] is not None})
            links = sorted({r["platform_links"] for r in matched if r["platform_links"] is not None})
            router_counts = sorted({r["platform_routers"] for r in matched if r["platform_routers"] is not None})
            processor_counts = sorted({r["platform_processors"] for r in matched if r["platform_processors"] is not None})
            speed_sets = sorted({r["platform_speed_factors"] for r in matched if r["platform_speed_factors"] is not None})
            frequency_sets = sorted({r["frequencies"] for r in matched if r["frequencies"] is not None})
            platform_note = f"Platform: nodes {nodes or 'n/a'} (processors {processor_counts or 'n/a'}, routers {router_counts or 'n/a'}); links {links or 'n/a'}; speed factors {speed_sets or 'n/a'}; frequencies {frequency_sets or 'n/a'}"
            fig.suptitle(f'{group["label"]}\n{platform_note}', fontsize=13, fontweight="bold")
            lines = line1 + line2
            ax_runtime.legend(lines, [line.get_label() for line in lines], loc="upper left")
            fig.tight_layout(rect=(0, 0, 1, 0.91))
            fig.savefig(folder / "performance.png", dpi=180, bbox_inches="tight")
            fig.savefig(folder / "performance.svg", bbox_inches="tight")
            plt.close(fig)

        fields = ["trial", "matched", "input_file", "input_source", "output_file", "output_source", "match_check", "tasks", "messages", "platform_nodes", "platform_processors", "platform_routers", "platform_links", "platform_speed_factors", "frequencies", "makespan", "scheduler_seconds", "sat", "run_status", "run_elapsed_seconds", "workers", "run_reported_seconds"]
        with (folder / "experimental_results.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        manifest = {
            "test": group["name"],
            "description": group["label"],
            "source_output_directory": group["output_dir"],
            "verified_pair_count": sum(r["matched"] for r in records),
            "output_count": len(records),
            "unmatched_outputs": unmatched_outputs,
            "input_only_files": orphan_inputs,
            "source_trial_summaries": summaries,
            "matching_policy": "Basename plus embedded job/message counts, output schedule size, and assigned-node membership in the input platform. Ambiguous metadata-compatible inputs use the preferred source directory order documented in build_evaluation.py.",
            "trials": records,
        }
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    fields = ["test", "trial", "matched", "input_file", "input_source", "output_file", "output_source", "tasks", "messages", "platform_nodes", "platform_processors", "platform_routers", "platform_links", "platform_speed_factors", "frequencies", "makespan", "scheduler_seconds", "sat", "run_status", "run_elapsed_seconds", "workers", "run_reported_seconds", "match_check"]
    with (DEST / "all_trials.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_records)

    readme = """# Scheduler Evaluation\n\nThis directory contains reviewable copies of the stress-test inputs and scheduler outputs, grouped by the numbered `job_stress_test` output folders. Original files remain in place. Each test folder has `input/`, `output/`, an experimental results CSV, a JSON manifest, and a plot when verified pairs contain runtime and makespan values.\n\n## Matching and interpretation\n\nA trial is counted as verified only when its output basename identifies an input candidate and the candidate's embedded job/message counts agree with the filename, its job count agrees with the scheduled job count, and every assigned output node exists in the candidate platform. Where duplicate input copies pass these checks, the preferred source directory order is listed in `build_evaluation.py`; the chosen source path is recorded in the manifest.\n\nThe plots show scheduler runtime and optimal makespan. Each x-axis label is `jobs/messages`; the title reports the platform node and link counts.\n\nUnmatched outputs and input-only files are listed in each test's `manifest.json` and `experimental_results.csv`. They are retained as evidence but are excluded from plots. In particular, the special `job_stress_test_4` output group has only one input currently available by matching basename (`100Tasks.json`); the other output files remain listed as unpaired. The generic `input/job_stress_test` currently contains inputs that do not have same-named outputs in `output/job_stress_test`, so they are listed as input-only.\n\n`all_trials.csv` combines all groups for spreadsheet review. `build_evaluation.py` regenerates this directory from the source folders.\n"""
    (DEST / "README.md").write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()

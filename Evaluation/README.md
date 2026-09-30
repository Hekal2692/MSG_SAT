# Scheduler Evaluation

This directory contains reviewable copies of the stress-test inputs and scheduler outputs, grouped by the numbered `job_stress_test` output folders. Original files remain in place. Each test folder has `input/`, `output/`, an experimental results CSV, a JSON manifest, and a plot when verified pairs contain runtime and makespan values.

## Matching and interpretation

A trial is counted as verified only when its output basename identifies an input candidate and the candidate's embedded job/message counts agree with the filename, its job count agrees with the scheduled job count, and every assigned output node exists in the candidate platform. Where duplicate input copies pass these checks, the preferred source directory order is listed in `build_evaluation.py`; the chosen source path is recorded in the manifest.

The plots show scheduler runtime and optimal makespan. Each x-axis label is `jobs/messages`; the title reports the platform node and link counts.

Unmatched outputs and input-only files are listed in each test's `manifest.json` and `experimental_results.csv`. They are retained as evidence but are excluded from plots. In particular, the special `job_stress_test_4` output group has only one input currently available by matching basename (`100Tasks.json`); the other output files remain listed as unpaired. The generic `input/job_stress_test` currently contains inputs that do not have same-named outputs in `output/job_stress_test`, so they are listed as input-only.

`all_trials.csv` combines all groups for spreadsheet review. `build_evaluation.py` regenerates this directory from the source folders.

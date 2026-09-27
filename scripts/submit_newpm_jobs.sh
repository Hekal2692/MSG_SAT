#!/usr/bin/env bash
# Submit the two NewPM cases as separate Slurm jobs.
set -euo pipefail

mkdir -p logs/slurm testOutput

for case_name in 100T_NewPM 250T_NewPM; do
    job_id=$(sbatch --parsable scripts/run_smt_scheduler.sbatch \
        "newInputFiles/${case_name}.json" \
        "testOutput/${case_name}_smt_output.json")
    echo "Submitted ${case_name}: job ${job_id}"
    echo "  live log: logs/slurm/smt-scheduler-${job_id}.out"
    echo "  error log: logs/slurm/smt-scheduler-${job_id}.err"
done

echo
echo "Monitor: squeue -u \"$USER\""
echo "Accounting after completion: sacct -j JOB_ID --format=JobID,JobName,State,Elapsed,Start,End,AllocCPUS,MaxRSS"

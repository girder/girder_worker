#!/bin/bash
#SBATCH --job-name=dummy_job
#SBATCH --time=00:05:00       # Set job runtime (hh:mm:ss)
#SBATCH --partition=girdercompute
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G

$@

# SBATCH --output=dummy_job.out
# SBATCH --error=dummy_job.err

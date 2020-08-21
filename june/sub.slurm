#!/bin/bash
#SBATCH --job-name=test
#SBATCH --partition=high-mem
#SBATCH --time=00:30:59
#SBATCH --nodes=1
#SBATCH --ntasks=4

cd /home/users/glister/JUNE/scripts
pwd

module load eb/OpenMPI/gcc/4.0.0

mpirun -n 4 python run_simulation.py

sacct -j $SLURM_JOBID --format=User,JobID,Jobname,partition,state,time,elapsed,MaxRss,nnodes,ncpus


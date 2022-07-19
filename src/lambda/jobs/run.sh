#!/bin/bash -l
export I_MPI_OFI_LIBRARY_INTERNAL=0
module load intelmpi
module load libfabric-aws
spack load ufs-weather-model
set -x
ulimit -s unlimited
ulimit -a

export FI_PROVIDER=efa
export I_MPI_DEBUG=5
export I_MPI_FABRICS=ofi
export I_MPI_OFI_PROVIDER=efa
export I_MPI_PIN_DOMAIN=omp
export KMP_AFFINITY=compact
export OMP_NUM_THREADS=4
export OMP_STACKSIZE=12G
export SLURM_EXPORT_ENV=ALL

time mpiexec.hydra $(which ufs_weather_model)

ftime=$(< /fsx/run/ftime)
y=${ftime:0:4}
m=${ftime:5:2}
d=${ftime:8:2}
h=${ftime:11:2}


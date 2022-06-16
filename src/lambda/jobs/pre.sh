#!/bin/bash -l
export I_MPI_OFI_LIBRARY_INTERNAL=0
module load intelmpi
module load libfabric-aws
spack load ufs-utils
set -x
ulimit -s unlimited
ulimit -a

cd /fsx/run
ftime=$(< /fsx/run/ftime)
y=${ftime:0:4}
m=${ftime:5:2}
d=${ftime:8:2}
h=${ftime:11:2}
sed -r -e "s/atm_files_input_grid=.*/atm_files_input_grid=\'gfs.t${h}z.atmanl.nc\'/;
	   s/sfc_files_input_grid=.*/sfc_files_input_grid=\'gfs.t${h}z.sfcanl.nc\'/;" \
	fort.41.in > fort.41
sed -r -e "s/(start_hour:).*/\1 ${h}/;
	   s/(start_day:).*/\1 ${d}/;
	   s/(start_month:).*/\1 ${m}/;
	   s/(start_year:).*/\1 ${y}/;" \
	model_configure.in > model_configure

for i in {0..6} ; do
  sed -i "5 s/.*/  DateStr='${y}-${m}-${d}_0${i}:00:00'/" /fsx/run/00${i}/itag
done

export FI_PROVIDER=efa
export I_MPI_DEBUG=5
export I_MPI_FABRICS=ofi
export I_MPI_OFI_PROVIDER=efa
export I_MPI_PIN_DOMAIN=omp
export KMP_AFFINITY=compact
export OMP_NUM_THREADS=4
export OMP_STACKSIZE=12G
export SLURM_EXPORT_ENV=ALL

time mpiexec.hydra $(which chgres_cube)

ln -fs ../gfs_ctrl.nc INPUT/gfs_ctrl.nc
for n in {1..6}; do
  ln -fs ../out.atm.tile$n.nc INPUT/gfs_data.tile$n.nc
  ln -fs ../out.sfc.tile$n.nc INPUT/sfc_data.tile$n.nc
done

aws s3 cp slurm-${SLURM_JOB_ID}.out s3://aws-weather-bucket/run/

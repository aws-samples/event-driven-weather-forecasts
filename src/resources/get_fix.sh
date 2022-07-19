#!/bin/bash

set -x

nco="https://ftp.emc.ncep.noaa.gov/static_files/public/UFS/GFS"

in_dir=run/INPUT
in_grid=( \
	grid_spec.nc
	C768_grid.tile[1-6].nc \
	C768_mosaic.nc \
	C768_oro_data.tile[1-6].nc \
)

fix_dir=run/fix
fix_sfc=( \
	C768.facsf.tile[1-6].nc \
	C768.maximum_snow_albedo.tile[1-6].nc \
	C768.slope_type.tile[1-6].nc \
	C768.snowfree_albedo.tile[1-6].nc \
	C768.soil_type.tile[1-6].nc \
	C768.substrate_temperature.tile[1-6].nc \
	C768.vegetation_greenness.tile[1-6].nc \
	C768.vegetation_type.tile[1-6].nc \
)
fix_am=( \
	CFSR.SEAICE.1982.2012.monthly.clim.grb \
	RTGSST.1982.2012.monthly.clim.grb \
	global_albedo4.1x1.grb \
	global_glacier.2x2.grb \
	global_hyblev.l65.txt \
	global_maxice.2x2.grb \
	global_mxsnoalb.uariz.t1534.3072.1536.rg.grb \
	global_shdmax.0.144x0.144.grb \
	global_shdmin.0.144x0.144.grb \
	global_slmask.t1534.3072.1536.grb \
	global_slope.1x1.grb \
	global_snoclim.1.875.grb \
	global_snowfree_albedo.bosu.t1534.3072.1536.rg.grb \
	global_soilmgldas.statsgo.t1534.3072.1536.grb \
	global_soiltype.statsgo.t1534.3072.1536.rg.grb \
	global_tg3clim.2.6x1.5.grb \
	global_vegfrac.0.144.decpercent.grb \
	global_vegtype.igbp.t1534.3072.1536.rg.grb \
)

fix_co2=( \
	global_co2historicaldata_[2009-2021].txt \
)

(
  test -d $in_dir || mkdir $in_dir
  cd $in_dir
  for file in ${in_grid[@]} ; do
    curl -O $nco/fix/fix_fv3/C768/$file
  done
  curl -O $nco/fix/fix_fv3/C768_gfdl/grid_spec.nc
)

(
  test -d $fix_dir || mkdir $fix_dir
  cd $fix_dir
  for file in ${fix_sfc[@]} ; do
    curl -O $nco/fix_nco_gfsv16/fix_fv3_gmted2010/C768/fix_sfc/$file
  done
  for file in ${fix_am[@]} ; do
    curl -O $nco/fix/fix_am/$file
  done
)

(
  cd run
  for file in ${fix_co2[@]} ; do
    curl  $nco/fix/fix_am/fix_co2_update/$file -o "co2historicaldata_#1.txt"
  done
)

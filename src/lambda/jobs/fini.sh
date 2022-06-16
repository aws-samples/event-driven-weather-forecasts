#!/bin/bash -l

set -x
ftime=$(< /fsx/run/ftime)
y=${ftime:0:4}
m=${ftime:5:2}
d=${ftime:8:2}
h=${ftime:11:2}

date -u +"%Y-%m-%dT%H:%M:%SZ" > forecast.done
aws s3 cp forecast.done s3://aws-weather-bucket/outputs/${y}/${m}/${d}/${h}/forecast.done
aws s3 cp slurm-${SLURM_JOB_ID}.out s3://aws-weather-bucket/run/

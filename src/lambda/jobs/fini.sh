#!/bin/bash -l

set -x
ftime=$(< /fsx/run/ftime)
y=${ftime:0:4}
m=${ftime:5:2}
d=${ftime:8:2}
h=${ftime:11:2}

date -u +"%Y-%m-%dT%H:%M:%SZ" > forecast.done

#!/usr/bin/env python3
import os

import aws_cdk as cdk

from wx.network import VpcStack
from wx.bucket import S3Stack
from wx.forecast import ForecastStack
from wx.pclusterapi import ParallelClusterApiStack
from wx.slurmdb import SlurmDbStack


props = {}

app = cdk.App()

wx = cdk.Stack(app, 'WX', env={"region": "us-east-2"})
cdk.Tags.of(wx).add("Purpose", "Event Driven Weather Forecast", priority=300)

vpc = VpcStack(wx, "vpc", props)

forecast = ForecastStack(wx, "forecast", vpc.outputs)
pcluster_api = ParallelClusterApiStack(wx, "parallel-cluster-api")

slurmdb = SlurmDbStack(wx, "slurmdbd", vpc.outputs)
slurmdb.add_dependency(vpc)


s3 = S3Stack(wx, "s3", vpc.outputs)
s3.add_dependency(forecast)
s3.add_dependency(pcluster_api)
s3.add_dependency(slurmdb)
s3.add_dependency(vpc)

app.synth()

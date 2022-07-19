# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    aws_s3 as s3,
    aws_s3_assets as assets,
    CfnOutput, Fn, NestedStack, Tags
)
from constructs import Construct


class S3(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id)

        bucket_name=kwargs["bucket"]
        self.bucket = s3.Bucket(self, "nwp-bucket",
                bucket_name=bucket_name
                )
        forecast_template = assets.Asset(self, "RunTemplate", path="resources/run")
        Tags.of(self.bucket).add("Purpose", "Event Driven Weather Forecast", priority=300)

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "ForecastTemplate", value=forecast_template.s3_object_url,
                export_name="ForecastTemplate")

    @property
    def outputs(self):
        return self.bucket


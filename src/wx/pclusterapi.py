# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
        aws_iam as iam,
        Aws, CfnOutput, CfnStack, CfnStackProps, Fn, NestedStack, Tags
)
from constructs import Construct

class ParallelClusterApiStack(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        aid = Aws.ACCOUNT_ID
        region = Aws.REGION
        version = "3.1.4"
        template_url = "https://aws-weather-bucket.s3.us-east-2.amazonaws.com/templates/parallelcluster-api.yaml"
        params = {
                "ApiDefinitionS3Uri": f"s3://{region}-aws-parallelcluster/parallelcluster/{version}/api/ParallelCluster.openapi.yaml",
                "EnableIamAdminAccess": "true",
                "CreateApiUserRole": "false",
                }

        self.api = CfnStack(self, "APITemplate",
                template_url=template_url,
                parameters=params)

        Tags.of(self.api).add("Purpose", "Event Driven Weather Forecast", priority=300)

        CfnOutput(self, "ParallelClusterApiInvokeUrl",
                  value=Fn.get_att(self.api.logical_id, "Outputs.ParallelClusterApiInvokeUrl").to_string(),
                  export_name="ParallelClusterApiInvokeUrl")


    @property
    def outputs(self):
        return self.api


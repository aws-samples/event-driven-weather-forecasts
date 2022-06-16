# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import datetime as dt
from aws_cdk import (
    aws_iam as iam,
    aws_lambda as λ,
    aws_lambda_event_sources as λ_events,
    aws_sns as sns,
    Aws, CfnOutput, Duration, Fn, NestedStack, Tags
)
from constructs import Construct


class ForecastStack(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.wx_sns = sns.Topic(self, "ForecastSns", display_name="Forecast SNS Topic")

        policy_doc = iam.PolicyDocument()
        policy_doc.add_statements(iam.PolicyStatement(
            actions=[
                "secretsmanager:GetResourcePolicy",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecretVersionIds",
                "secretsmanager:ListSecrets",
                ],
            resources=["*"],
            effect=iam.Effect.ALLOW))
        role = iam.Role(self, "Role",
                assumed_by=iam.CompositePrincipal(
                    iam.ServicePrincipal("lambda.amazonaws.com"),
                    iam.ServicePrincipal("sts.amazonaws.com"),
                ),
                description="CreateForecastLambdaRole",
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                    ],
                inline_policies=[policy_doc],
        )

        layer = λ.LayerVersion(self, "lambda_layer",
                compatible_runtimes=[λ.Runtime.PYTHON_3_9],
                code=λ.Code.from_asset("./layer.zip"),
                layer_version_name="wx_layer",
                description="WX Lambda Layer",
            )

        run = λ.Function(self, "lambda_func_run",
                code=λ.Code.from_asset("./lambda"),
                handler="forecast.main",
                layers=[layer],
                role=role,
                runtime=λ.Runtime.PYTHON_3_9,
                timeout=Duration.seconds(60),
                vpc=vpc,
            )
        Tags.of(run).add("Purpose", "Event Driven Weather Forecast", priority=300)
        run.add_event_source(λ_events.SnsEventSource(self.wx_sns))

        CfnOutput(self, "ForecastSnsArn", value=self.wx_sns.topic_arn,
                export_name="ForecastSnsArn")

    @property
    def outputs(self):
        return self.wx_sns


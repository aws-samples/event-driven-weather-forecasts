# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as λ,
    aws_lambda_event_sources as λ_events,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_assets as assets,
    aws_s3_notifications,
    aws_sns as sns,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    Aws, CfnOutput, Duration, Fn, NestedStack, Tags
)
from constructs import Construct


class S3Stack(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        post_head = assets.Asset(self, "PostComputeFileAsset",
                path="resources/post_install_headnode.sh")
        cluster_name = "wx-pcluster"

        purl = Fn.import_value("ParallelClusterApiInvokeUrl")
        hostname = Fn.select(2, Fn.split("/", Fn.select(0, Fn.split('.', purl))))
        parn = f"arn:aws:execute-api:{Aws.REGION}::{hostname}/*/*/*"

        jwt_key = Fn.import_value("JWTKey")
        sns_topic = Fn.import_value("ForecastSnsArn")

        sg_rds = ec2.SecurityGroup(
                self,
                id="sg_slurm",
                vpc=vpc,
                security_group_name="sg_slurm"
        )

        sg_rds.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(8080)
        )

        policy_doc = iam.PolicyDocument(statements=[
            iam.PolicyStatement(
                actions=["execute-api:Invoke", "execute-api:ManageConnections"],
                resources=["arn:aws:execute-api:*:*:*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions=["states:*"],
                resources=["*"],
                effect=iam.Effect.ALLOW),
            iam.PolicyStatement(
                actions=["iam:*"],
                resources=["*"],
                effect=iam.Effect.ALLOW),
        ])
        lambda_role = iam.Role(self, "Role",
                assumed_by=iam.CompositePrincipal(
                    iam.ServicePrincipal("lambda.amazonaws.com"),
                    iam.ServicePrincipal("sts.amazonaws.com"),
                ),
                description="CreateAPILambdaRole",
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                    ],
                inline_policies=[policy_doc],
        )

        subnet = vpc.public_subnets[1].subnet_id
        for net in vpc.public_subnets:
            if net.availability_zone == "us-east-2b":
                subnet = net

        layer = λ.LayerVersion(self, "lambda_layer",
                                      compatible_runtimes=[λ.Runtime.PYTHON_3_9],
                                      code=λ.Code.from_asset("./layer.zip"),
                                      layer_version_name="wx_layer",
                                      description="WX Lambda Layer",
                                    )

        destroy = λ.Function(self, "lambda_func_destroy",
                code=λ.Code.from_asset("./lambda"),
                environment={
                    "CLUSTER_NAME": cluster_name,
                    "PCLUSTER_API_URL": purl,
                    "REGION": Aws.REGION,
                },
                handler="cluster.destroy",
                layers=[layer],
                log_retention=logs.RetentionDays.ONE_DAY,
                role=lambda_role,
                runtime=λ.Runtime.PYTHON_3_9,
                timeout=Duration.seconds(60)
            )
        Tags.of(destroy).add("Purpose", "Event Driven Weather Forecast", priority=300)

        self.bucket = s3.Bucket.from_bucket_arn(self, "nwp-bucket",
                bucket_arn="arn:aws:s3:::aws-weather-bucket"
            )
        Tags.of(self.bucket).add("Purpose", "Event Driven Weather Forecast", priority=300)

        #self.bucket = s3.Bucket(self, "nwp-bucket",
        #        bucket_name="aws-weather-bucket"
        #        )

        outputs = aws_s3_notifications.LambdaDestination(destroy)
        self.bucket.add_event_notification(s3.EventType.OBJECT_CREATED, outputs,
                s3.NotificationKeyFilter(prefix="outputs/", suffix="done"))

        forecast_wait = sfn.Wait(self, "WaitForForecast",
                time=sfn.WaitTime.duration(Duration.minutes(60)))

        destroy_cluster = tasks.LambdaInvoke(self, "TaskDestroyCluster",
                lambda_function=destroy,
                output_path="$.Payload",
                )

        definition = forecast_wait.next(destroy_cluster)

        sm = sfn.StateMachine(self, "WXStateMachine",
            definition=definition,
            timeout=Duration.minutes(65))

        Tags.of(sm).add("Purpose", "Event Driven Weather Forecast", priority=300)

        create = λ.Function(self, "lambda_func_create",
                code=λ.Code.from_asset("./lambda"),
                environment={
                    "CLUSTER_NAME": cluster_name,
                    "JWTKEY": jwt_key,
                    "PCLUSTER_API_URL": purl,
                    "REGION": Aws.REGION,
                    "S3_URL_POST_INSTALL_HEADNODE": f"{post_head.s3_object_url}",
                    "SG": sg_rds.security_group_id,
                    "SNS_TOPIC": sns_topic,
                    "SM_ARN": sm.state_machine_arn,
                    "SUBNETID": subnet,
                },
                handler="cluster.create",
                layers=[layer],
                log_retention=logs.RetentionDays.ONE_DAY,
                role=lambda_role,
                runtime=λ.Runtime.PYTHON_3_9,
                timeout=Duration.seconds(60)
            )
        Tags.of(create).add("Purpose", "Event Driven Weather Forecast", priority=300)
        gfs = sns.Topic.from_topic_arn(self, "NOAAGFS", "arn:aws:sns:us-east-1:123901341784:NewGFSObject")
        create.add_event_source(λ_events.SnsEventSource(gfs))

        CfnOutput(self, "S3 Bucket", value=self.bucket.bucket_name)
        CfnOutput(self, "StateMachineArn", value=sm.state_machine_arn,
                export_name="StateMachineArn")


    @property
    def outputs(self):
        return self.bucket


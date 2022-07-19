# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    App, CfnOutput, Fn, NestedStack, RemovalPolicy
)

from constructs import Construct

class SlurmDb(NestedStack):
    def __init__(self, scope:Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id)

        vpc = kwargs["vpc"]
        sg_rds = ec2.SecurityGroup(
                self,
                id="sg_rds",
                vpc=vpc,
                security_group_name="sg_rds"
        )

        sg_rds.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(3306)
        )

        self.username = "admin"
        self.secret = secretsmanager.Secret(self, "DBCreds",
                secret_name="SlurmDbCreds",
                description="Slurm RDS Credentials",
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    exclude_characters ="\"@/\\ '",
                    generate_string_key="password",
                    secret_string_template=f'{{"username":"{self.username}"}}')
                )

        instance_type = ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MEDIUM)
        engine_version = rds.MysqlEngineVersion.VER_8_0_28

        self.db = rds.DatabaseInstance(self, "RDS",
            credentials=rds.Credentials.from_secret(self.secret, self.username),
            database_name="slurmdb",
            delete_automated_backups=True,
            deletion_protection=False,
            engine=rds.DatabaseInstanceEngine.mysql(version=engine_version),
            instance_type=instance_type,
            removal_policy=RemovalPolicy.DESTROY,
            security_groups=[sg_rds],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )

        self.jwt = secretsmanager.Secret(self, "JWTCreds",
                secret_name="JWTKey",
                description="JSON Web Token for SLURM"
                )

        CfnOutput(self, "hostname", value=self.db.db_instance_endpoint_address)
        CfnOutput(self, "DBSecretArn", value=self.secret.secret_full_arn,
                export_name="DBSecretArn")
        CfnOutput(self, "JWTKeyArn", value=self.jwt.secret_full_arn,
                export_name="JWTKeyArn")
        CfnOutput(self, "JWTKey", value="JWTKey", export_name="JWTKey")

    @property
    def outputs(self):
        return self.db

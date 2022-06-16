# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    aws_ec2 as ec2,
    CfnOutput, NestedStack, Tags
)
from constructs import Construct

class VpcStack(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, props: None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        env_name = self.node.try_get_context("env")

        vpc = ec2.Vpc(self, 'wx-vpc',
            cidr = '10.0.0.0/18',
            enable_dns_hostnames = True,
            enable_dns_support = True,
            max_azs = 2,
            nat_gateways = 1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask = 20,
                    name = 'public',
                    subnet_type = ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    cidr_mask = 20,
                    name = 'private',
                    subnet_type = ec2.SubnetType.PRIVATE_WITH_NAT
                ),
            ],
        )

        fsx_security_group = ec2.SecurityGroup(
            self,
            "FsxSg",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name="fsx-lustre-sg",
        )

        fsx_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(988),
            description="FSx Lustre",
        )

        CfnOutput(self, "vpcid", value=vpc.vpc_id)
        [CfnOutput(self,f"PublicSubnet{i}", value=x.subnet_id) for i,x in enumerate(vpc.public_subnets)]
        [CfnOutput(self,f"PrivateSubnet{i}", value=x.subnet_id) for i,x in enumerate(vpc.private_subnets)]
        [CfnOutput(self,f"IsolatedSubnet{i}", value=x.subnet_id) for i,x in enumerate(vpc.isolated_subnets)]

        self.vpc = vpc
        Tags.of(self.vpc).add("Purpose", "Event Driven Weather Forecast", priority=300)

    @property
    def outputs(self):
        return self.vpc

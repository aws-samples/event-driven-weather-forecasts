# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import datetime as dt
import os
import re

import boto3
import botocore
import json
import requests
import yaml

baseurl = os.getenv("PCLUSTER_API_URL")
cluster_name = os.getenv("CLUSTER_NAME", "wx-pcluster")
region = os.getenv("REGION", "us-east-2")
path = f"{baseurl}/v3/clusters"

def gateway(url, method, data):

    req_call = {
        "POST": requests.post,
        "GET": requests.get,
        "PUT": requests.put,
        "PATCH": requests.patch,
        "DELETE": requests.delete,
    }.get(method)

    print(f"url: {url}")
    session = botocore.session.Session()
    request = botocore.awsrequest.AWSRequest(method=method, url=url, data=data)
    botocore.auth.SigV4Auth(session.get_credentials(), "execute-api", region).add_auth(request)
    boto_request = request.prepare()
    boto_request.headers["content-type"] = "application/json"
    response = req_call(url, data=data, headers=boto_request.headers, timeout=30)
    code = response.status_code
    print(f"Response code: {code}")
    return response.json()

def destroy(event, context):
    print(event)

    c = boto3.client("iam")
    roles = c.list_roles()
    for role in roles['Roles']:
        n = role['RoleName']
        if n.startswith(f"{cluster_name}-Role") and not n.startswith(f"{cluster_name}-RoleHeadNode"):
            policies = c.list_attached_role_policies(RoleName=n)
            for policy in policies['AttachedPolicies']:
                c.detach_role_policy(RoleName=n, PolicyArn=policy['PolicyArn'])

    params = {"region": region}
    data = json.dumps({"clusterName": cluster_name})
    method = "DELETE"
    url = f"{path}/{cluster_name}?region={region}"
    print(gateway(url, method, data))

def create(event, context):

    msg = json.loads(event["Records"][0]["Sns"]["Message"])
    key = msg['Records'][0]['s3']['object']['key']
    print(f"Key: {key}")
    p = re.compile(r"""
                 gfs.                      # GFS prefix
                 (?P<y>\d{4})              # Year
                 (?P<m>\d{2})              # Month
                 (?P<d>\d{2})              # Day
                 /(?P<h>\d{2})             # Hour
                 /atmos                    # Atmospheric components
                 /gfs.t(?P=h)z.atmanl.nc   # Filename
                 """,
                 re.VERBOSE)
    m = p.match(key)
    if not m:
        return

    ftime = f"{m.group('y')}-{m.group('m')}-{m.group('d')}T{m.group('h')}:00:00Z"
    stack_name = os.getenv("STACK_NAME")
    sm_arn = ""
    outputs = boto3.Session().client("cloudformation").describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    for o in outputs:
      if o["OutputKey"] == "StateMachineArn":
        sm_arn = o["OutputValue"]
        break
    sfn = boto3.client('stepfunctions')
    sfn.start_execution(
        stateMachineArn=sm_arn
    )

    with open("hpc6a.yaml", "r") as cf:
        config_data = yaml.safe_load(cf)

    config_data['Region'] = region
    config_data['HeadNode']['Networking']['SubnetId'] = os.getenv('SUBNETID')
    config_data['HeadNode']['Networking']['AdditionalSecurityGroups'][0] = os.getenv('SG')
    config_data['Scheduling']['SlurmQueues'][0]['Networking']['SubnetIds'][0] = os.getenv('SUBNETID')

    config_data['HeadNode']['CustomActions']['OnNodeConfigured']['Script'] = os.getenv('S3_URL_POST_INSTALL_HEADNODE')
    config_data['HeadNode']['CustomActions']['OnNodeConfigured']['Args'][0] = region
    config_data['HeadNode']['CustomActions']['OnNodeConfigured']['Args'][1] = os.getenv('SNS_TOPIC')
    config_data['HeadNode']['CustomActions']['OnNodeConfigured']['Args'][2] = ftime
    config_data['HeadNode']['CustomActions']['OnNodeConfigured']['Args'][3] = os.getenv("JWTKEY")

    method = "POST"
    data = json.dumps({"clusterConfiguration": yaml.dump(config_data, default_flow_style=False),
        "clusterName": cluster_name})
    print(data)
    print(gateway(path, method, data))


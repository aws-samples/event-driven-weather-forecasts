# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from functools import lru_cache
import os

import boto3
import botocore
import json
import requests

region = os.getenv("AWS_REGION")
ip = "127.0.0.1"
template = {
    "job": {
        "name":"",
        "nodes":1,
        "cpus_per_task": 4,
        "tasks_per_node": 24,
        "current_working_directory":"/fsx/run",
        "environment":{
            "PATH":"/bin:/usr/bin/:/usr/local/bin/",
            "LD_LIBRARY_PATH":"/lib/:/lib64/:/usr/local/lib"
        },
        "requeue": "false"
    },
    "script": ""
}

@lru_cache
def token():
    session = boto3.session.Session()
    sm = session.client('secretsmanager')
    secret = sm.get_secret_value(SecretId="JWTKey")
    return secret['SecretString']

@lru_cache
def headers():
    return {
            "X-SLURM-USER-NAME": "ec2-user",
            "X-SLURM-USER-TOKEN": token(),
            "content-type": "application/json",
            }

def submit(data):
    global ip
    url = f"http://{ip}:8080/slurm/v0.0.37/job/submit"
    resp = requests.post(url, data=json.dumps(data), headers=headers())
    jid = resp.json()["job_id"]
    print(resp.json())
    print(resp.status_code)
    return jid

def status(jobid, headers):
    global ip
    url = f"http://{ip}:8080/slurm/v0.0.37/job/{jobid}"
    resp = requests.post(url, headers=headers())
    print(resp.json())

def pre():
    with open("jobs/pre.sh", "r") as f:
        script = f.read()
    template["job"]["name"] = "pre"
    template["job"]["nodes"] = 20
    template["script"] = script
    print(template)
    return submit(template)

def run(pid):
    with open("jobs/run.sh", "r") as f:
        script = f.read()
    template["job"]["name"] = "ufs"
    template["job"]["nodes"] = 20
    template["job"]["dependency"] = f"afterok:{pid}"
    template["script"] = script
    print(template)
    return submit(template)

def post(pid):
    with open("jobs/post.sh", "r") as f:
        script = f.read()
    template["job"]["nodes"] = 1
    jids = []
    for i in range(0, 7):
        template["job"]["name"] = f"post-{i:03}"
        template["job"]["dependency"] = f"afterok:{pid}"
        template["job"]["current_working_directory"] = f"/fsx/run/{i:03}"
        template["script"] = script
        print(template)
        jids.append(submit(template))
    return jids

def fini(ids):
    with open("jobs/fini.sh", "r") as f:
        script = f.read()
    template["job"]["nodes"] = 1
    template["job"]["name"] = "fini"
    template["job"]["tasks_per_node"] = 1
    template["job"]["dependency"] = f"afterok:{':'.join([str(x) for x in ids])}"
    template["script"] = script
    print(template)
    return submit(template)

def main(event, context):

    global ip

    print(event)
    subject = event['Records'][0]['Sns']['Subject']
    ip = event['Records'][0]['Sns']['Message']

    if subject != "Parallel Cluster Post Install - SUCCESS":
        return 1

    pid = pre()
    fid = run(pid)
    pids = post(fid)
    fini(pids)


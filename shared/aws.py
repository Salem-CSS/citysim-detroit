"""AWS clients shared by agent/, residents/ and infra/.

Bedrock can live in another AWS account. Set BEDROCK_ROLE_ARN (a role in that account that trusts ours,
see infra/bedrock-role.yaml) and every Bedrock call borrows that role; the other account pays and its
quotas apply. Leave it empty to call Bedrock in this account.

    from shared.aws import bedrock_runtime
    bedrock_runtime().converse(...)
"""
from __future__ import annotations

import os
import time

_cache: dict = {"client": None, "expires": 0.0}


def bedrock_runtime(sts=None, factory=None):
    import boto3

    factory = factory or boto3.client
    region = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
    role = os.environ.get("BEDROCK_ROLE_ARN", "")
    if not role:
        return factory("bedrock-runtime", region_name=region)
    if _cache["client"] is not None and time.time() < _cache["expires"] - 300:
        return _cache["client"]
    sts = sts or factory("sts")
    kw = {"RoleArn": role, "RoleSessionName": f"citysim-{os.environ.get('STAGE', 'dev')}", "DurationSeconds": 3600}
    if os.environ.get("BEDROCK_EXTERNAL_ID"):
        kw["ExternalId"] = os.environ["BEDROCK_EXTERNAL_ID"]
    creds = sts.assume_role(**kw)["Credentials"]
    client = factory("bedrock-runtime", region_name=region, aws_access_key_id=creds["AccessKeyId"],
                     aws_secret_access_key=creds["SecretAccessKey"], aws_session_token=creds["SessionToken"])
    exp = creds["Expiration"]
    _cache.update(client=client, expires=exp.timestamp() if hasattr(exp, "timestamp") else time.time() + 3600)
    return client

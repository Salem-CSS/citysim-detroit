import datetime as dt

from shared import aws


class FakeSTS:
    def __init__(self):
        self.calls = []

    def assume_role(self, **kw):
        self.calls.append(kw)
        return {"Credentials": {"AccessKeyId": "A", "SecretAccessKey": "S", "SessionToken": "T",
                                "Expiration": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)}}


def factory(name, **kw):
    return (name, kw)


def test_same_account_when_no_role(monkeypatch):
    monkeypatch.delenv("BEDROCK_ROLE_ARN", raising=False)
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    assert aws.bedrock_runtime(factory=factory) == ("bedrock-runtime", {"region_name": "us-east-1"})


def test_assumes_role_in_other_account_and_caches(monkeypatch):
    aws._cache.update(client=None, expires=0)
    monkeypatch.setenv("BEDROCK_ROLE_ARN", "arn:aws:iam::111122223333:role/citysim-bedrock-access")
    monkeypatch.setenv("BEDROCK_EXTERNAL_ID", "citysim-detroit")
    monkeypatch.setenv("STAGE", "salem")
    sts = FakeSTS()
    name, kw = aws.bedrock_runtime(sts=sts, factory=factory)
    assert name == "bedrock-runtime" and kw["aws_session_token"] == "T"
    assert sts.calls[0]["ExternalId"] == "citysim-detroit" and sts.calls[0]["RoleSessionName"] == "citysim-salem"
    aws.bedrock_runtime(sts=sts, factory=factory)
    assert len(sts.calls) == 1                     # cached until near expiry

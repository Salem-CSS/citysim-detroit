"""Get the Bedrock client from shared.aws.bedrock_runtime() (handles dual-account mode).
Send 25-resident batches to Bedrock (Nova 2 Lite) using prompt.build(); validate with validate.check(); retry failed residents once in a smaller batch; exponential backoff on 429s."""

def main(*args, **kwargs):
    raise NotImplementedError("batch")

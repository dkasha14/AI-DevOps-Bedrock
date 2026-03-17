import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def embed(text: str) -> list[float]:
    body = json.dumps({"inputText": text})
    resp = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
        body=body,
        accept="application/json",
        contentType="application/json"
    )
    output = json.loads(resp["body"].read())
    return output["embedding"]


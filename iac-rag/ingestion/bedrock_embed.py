import json
import boto3
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from botocore.exceptions import ClientError, EndpointConnectionError
from ingestion.config import settings

client = boto3.client('bedrock-runtime', region_name=settings.bedrock_region)
print("region_name",settings.bedrock_region,settings.bedrock_embed_model)
@retry(retry=retry_if_exception_type((ClientError, EndpointConnectionError)),
       wait=wait_exponential(multiplier=0.6, min=1, max=20),
       stop=stop_after_attempt(7))
def embed_text(text: str) -> list:
    text = text[: settings.embed_max_chars]
    body = {"inputText": text}
    res = client.invoke_model(
        modelId=settings.bedrock_embed_model,
        contentType='application/json',
        accept='application/json',
        body=json.dumps(body)
    )
    payload = json.loads(res['body'].read())
    return payload.get('embedding')  # list[float]

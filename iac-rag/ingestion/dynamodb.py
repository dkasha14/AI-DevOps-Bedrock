import boto3
from ingestion.config import settings

ddb = boto3.resource('dynamodb', region_name=settings.aws_region)
table = ddb.Table(settings.ddb_table)

def upsert_catalog(item: dict):
    table.put_item(Item=item)

def get_existing_commit(module_name: str, version: str, path: str) -> str | None:
    resp = table.get_item(
        Key={"pk": f"MOD#{module_name}", "sk": f"VER#{version}#PATH#{path}"}
    )
    return (resp.get('Item') or {}).get('commit_sha')

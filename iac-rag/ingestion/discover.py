import boto3
from typing import Iterator, Tuple
from ingestion.config import settings

s3 = boto3.client('s3', region_name=settings.aws_region)

def list_module_versions() -> Iterator[Tuple[str, str, str]]:
    """Yield (module_name, version, s3_prefix)"""
    paginator = s3.get_paginator('list_objects_v2')
    prefix = f"{settings.s3_prefix}/"
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix, Delimiter='/'):
        for mod in page.get('CommonPrefixes', []):
            mod_name = mod['Prefix'].split('/')[-2]
            for page2 in paginator.paginate(Bucket=settings.s3_bucket, Prefix=f"{prefix}{mod_name}/", Delimiter='/'):
                for ver in page2.get('CommonPrefixes', []):
                    version = ver['Prefix'].split('/')[-2]
                    yield mod_name, version, ver['Prefix']

def iter_files(module_prefix: str):
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=module_prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.tf') or key.endswith('.md') or key.endswith('COMMIT_SHA'):
                yield key

def read_s3(key: str) -> str:
    obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
    return obj['Body'].read().decode('utf-8', errors='ignore')

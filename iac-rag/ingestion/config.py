from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    aws_region: str = "us-east-1"

    # S3 mirror
    s3_bucket: str = "iac-rag-prod-modules-private"
    s3_prefix: str = "modules"

    # Bedrock
    bedrock_region: str = "us-east-1"
    bedrock_embed_model: str = "amazon.titan-embed-text-v2:0"
    embed_max_chars: int = 8000  # guard input size

    # OpenSearch Serverless (AOSS)
    aoss_host: str  = "3o3suhk7jd9kb315ub4e.us-east-1.aoss.amazonaws.com"
    aoss_collection: str = "dk-iac-rag-prod-vec"   # friendly name; not used in API calls
    aoss_index: str = "iac-rag-prod-vec"           # index inside the collection
    aoss_knn_dim: int = 1024                    # must match Titan embed dim
    aoss_bulk_size: int = 500

    # DynamoDB
    ddb_table: str = "tf_module_catalog"

    dry_run: bool = False

    class Config:
        env_file = ".env"

settings = Settings()


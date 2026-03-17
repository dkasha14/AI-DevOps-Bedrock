from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3

# --- Auth ---
session = boto3.Session()
credentials = session.get_credentials()
region = "us-east-1"
auth = AWSV4SignerAuth(credentials, region, "aoss")

# --- Client ---
host = "3o3suhk7jd9kb315ub4e.us-east-1.aoss.amazonaws.com"
client = OpenSearch(
    hosts=[{"host": host, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

# --- Index definition ---
index_name = "dk-iac-rag-prod-vec"

index_body = {
    "settings": {
        "index": {
            "knn": True  # enable vector search
        }
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "content": {"type": "text"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1536  # match your embedding size (OpenAI, etc.)
            },
        }
    },
}

# --- Create index if missing ---
if not client.indices.exists(index=index_name):
    resp = client.indices.create(index=index_name, body=index_body)
    print("Created index:", resp)
else:
    print(f"Index '{index_name}' already exists")

# --- Index a test document ---
doc = {
    "id": "1",
    "content": "Hello from AOSS!",
    "embedding": [0.01] * 1536  # fake vector just to test
}
resp = client.index(index=index_name, body=doc)
print("Indexed document:", resp["_id"])


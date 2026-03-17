import logging
from opensearchpy.exceptions import RequestError
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.helpers import bulk
from opensearchpy import AWSV4SignerAuth
from ingestion.config import settings

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- AWS Auth + Client ---
session = boto3.Session()
credentials = session.get_credentials()
auth = AWSV4SignerAuth(credentials, settings.aws_region, service="aoss")

client = OpenSearch(
    hosts=[{"host": settings.aoss_host, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)


# --- Helpers ---
def sanitize_tags(tags):
    """Ensure tags are strings (AOSS keyword fields require string values)."""
    if not tags:
        return []
    return [str(t) for t in tags if t is not None]


def ensure_index():
    """
    No-op since AOSS indexes must be created ahead of time.
    """
    logger.info("Skipping ensure_index – index is managed in AOSS")


def to_doc(chunk) -> dict:
    if isinstance(chunk, dict):
        doc = chunk
    elif hasattr(chunk, "dict"):  # Pydantic models
        doc = chunk.dict()
    else:  # generic object with attributes
        doc = vars(chunk)

    # --- ✅ Validate embedding dimension ---
    embedding = doc.get("embedding") or []
    if embedding and len(embedding) != 1024:  # must match AOSS index dim
        logger.warning(
            f"⚠️ Skipping {doc.get('path')} "
            f"(embedding dim {len(embedding)} != 1536)"
        )
        return None

    return {
        "_op_type": "index",
        "_index": settings.aoss_collection,
        "doc_id": str(doc.get("doc_id")),
        "module_name": str(doc.get("module_name")),
        "commit_version": str(doc.get("version")),
        "path": str(doc.get("path")),
        "block_type": str(doc.get("block_type")),
        "provider": str(doc.get("provider")),
        "services": [str(s) for s in (doc.get("services") or [])],
        "inputs": [str(i) for i in (doc.get("inputs") or [])],
        "outputs": [str(o) for o in (doc.get("outputs") or [])],
        "tags": [str(t) for t in (doc.get("tags") or [])],
        "owners": [str(o) for o in (doc.get("owners") or [])],
        "maturity": str(doc.get("maturity") or ""),
        "region_allowed": str(doc.get("region_allowed") or ""),
        "commit_sha": str(doc.get("commit_sha")),
        "text": doc.get("text_context") or "",
        "code": doc.get("code_normalized") or "",
        "vector": embedding,
    }


def bulk_index(chunks):
    # Build docs only if they have embeddings
    actions = [to_doc(c) for c in chunks if getattr(c, "embedding", None)]
    actions = [a for a in actions if a]  # remove None (skipped docs)

    if not actions:
        logger.warning("⚠️ No valid actions to index (missing/invalid embeddings).")
        return 0, []

    for action in actions:
        try:
            logger.info(f"Indexing document: {json.dumps(action, indent=2)}")
            ok, fail = bulk(
                client,
                [action],
                chunk_size=settings.aoss_bulk_size,
                request_timeout=120,
            )
        except RequestError as e:
            logger.error(f"❌ Error indexing document: {json.dumps(action, indent=2)}")
            logger.error(f"❌ Error message: {e}")
            return 0, []

    return ok, fail


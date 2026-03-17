from typing import List
from ingestion.models import Chunk

def enrich(chunks: List[Chunk], module_name: str, version: str) -> List[Chunk]:
    for c in chunks:
        if c.block_type == 'resource' and c.services:
            c.tags = sorted(set(c.tags + [f"svc:{s}" for s in c.services]))
        c.tags = sorted(set(c.tags + [f"module:{module_name}", f"ver:{version}"]))
    return chunks

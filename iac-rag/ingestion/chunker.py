from typing import List
from ingestion.models import Chunk

def enforce_size(chunks: List[Chunk], max_chars: int) -> List[Chunk]:
    out = []
    for c in chunks:
        # Split ONLY if a single field is too large, retain semantics
        if c.text_context and len(c.text_context) > max_chars:
            for i in range(0, len(c.text_context), max_chars):
                nc = c.model_copy()
                nc.text_context = c.text_context[i:i+max_chars]
                out.append(nc)
        elif c.code_normalized and len(c.code_normalized) > max_chars:
            for i in range(0, len(c.code_normalized), max_chars):
                nc = c.model_copy()
                nc.code_normalized = c.code_normalized[i:i+max_chars]
                out.append(nc)
        else:
            out.append(c)
    return out

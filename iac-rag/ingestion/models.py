from pydantic import BaseModel, Field
from typing import List, Optional

class Chunk(BaseModel):
    doc_id: str
    module_name: str
    version: str
    path: str
    block_type: str                    # resource|module|variable|output|example|readme
    provider: str = "aws"
    services: List[str] = Field(default_factory=list)
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    owners: List[str] = Field(default_factory=list)
    maturity: Optional[str] = None
    region_allowed: Optional[List[str]] = None
    commit_sha: Optional[str] = None

    code_normalized: Optional[str] = None
    text_context: Optional[str] = None
    embedding: Optional[List[float]] = None

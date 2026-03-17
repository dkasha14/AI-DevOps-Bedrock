import re, hashlib
import hcl2
from typing import List, Dict, Any, Tuple
from ingestion.discover import read_s3
from ingestion.models import Chunk

def _mk_id(module_name: str, version: str, path: str) -> str:
    return hashlib.sha256(f"{module_name}|{version}|{path}".encode()).hexdigest()

def _normalize_code(hcl: str) -> str:
    # Strip comments + blank lines
    hcl = re.sub(r'(?m)^\s*#.*$', '', hcl)
    hcl = re.sub(r'(?s)/\*.*?\*/', '', hcl)
    return '\n'.join([ln.rstrip() for ln in hcl.splitlines() if ln.strip()])

def _split_md(md: str) -> List[Tuple[str, str]]:
    lines = md.splitlines()
    sections, current = [], ('README', [])
    for ln in lines:
        if ln.startswith('#'):
            if current[1]:
                sections.append((current[0], '\n'.join(current[1]).strip()))
            current = (ln.strip('# ').strip(), [])
        else:
            current[1].append(ln)
    if current[1]:
        sections.append((current[0], '\n'.join(current[1]).strip()))
    return sections

def _normalize_block(blocks: Any) -> List[Dict[str, Any]]:
    """
    Ensure terraform blocks are always returned as a list of dicts.
    hcl2 sometimes returns: { ... } or [ { ... }, { ... } ]
    """
    if blocks is None:
        return []
    if isinstance(blocks, dict):
        return [blocks]
    if isinstance(blocks, list):
        return blocks
    return []

def parse_module_file(module_name: str, version: str, key: str, commit_sha: str) -> List[Chunk]:
    text = read_s3(key)
    chunks: List[Chunk] = []

    # Handle markdown files
    if key.endswith('.md'):
        for title, body in _split_md(text):
            chunks.append(Chunk(
                doc_id=_mk_id(module_name, version, f"{key}:{title}"),
                module_name=module_name, version=version, path=key,
                block_type='readme', text_context=f"# {title}\n\n{body}",
                code_normalized=None, commit_sha=commit_sha
            ))
        return chunks

    # Skip non-Terraform, non-Markdown files
    if not key.endswith('.tf'):
        return chunks

    # Parse terraform files with hcl2
    try:
        obj = hcl2.loads(text)
    except Exception as e:
        print(f"[WARN] Failed to parse {key} with hcl2: {e}")
        return chunks

    # --- Resources ---
    for res in _normalize_block(obj.get("resource")):
        for rtype, resdict in res.items():
            for name, body in resdict.items():
                chunks.append(Chunk(
                    doc_id=_mk_id(module_name, version, f"{key}:resource:{name}"),
                    module_name=module_name, version=version, path=key,
                    block_type='resource',
                    services=[rtype.split("_", 1)[0]],
                    code_normalized=_normalize_code(text),
                    text_context=None,
                    commit_sha=commit_sha
                ))

    # --- Modules ---
    for mod in _normalize_block(obj.get("module")):
        for mname, defs in mod.items():
            chunks.append(Chunk(
                doc_id=_mk_id(module_name, version, f"{key}:module:{mname}"),
                module_name=module_name, version=version, path=key,
                block_type='module',
                code_normalized=_normalize_code(text),
                text_context=None,
                commit_sha=commit_sha
            ))

    # --- Variables ---
    for v in _normalize_block(obj.get("variable")):
        for vname, defs in v.items():
            desc = ''
            if isinstance(defs, list) and defs and isinstance(defs[0], dict):
                desc = defs[0].get("description", "")
            chunks.append(Chunk(
                doc_id=_mk_id(module_name, version, f"{key}:variable:{vname}"),
                module_name=module_name, version=version, path=key,
                block_type='variable',
                inputs=[vname],
                code_normalized=_normalize_code(text),
                text_context=desc or None,
                commit_sha=commit_sha
            ))

    # --- Outputs ---
    for o in _normalize_block(obj.get("output")):
        for oname, defs in o.items():
            chunks.append(Chunk(
                doc_id=_mk_id(module_name, version, f"{key}:output:{oname}"),
                module_name=module_name, version=version, path=key,
                block_type='output',
                outputs=[oname],
                code_normalized=_normalize_code(text),
                text_context=None,
                commit_sha=commit_sha
            ))

    return chunks


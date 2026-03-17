from rich import print
from ingestion.config import settings
from ingestion.discover import list_module_versions, iter_files, read_s3
from ingestion.parse_hcl import parse_module_file
from ingestion.chunker import enforce_size
from ingestion.normalize import enrich
from ingestion.bedrock_embed import embed_text
from ingestion.opensearch import ensure_index, bulk_index
from ingestion.dynamodb import upsert_catalog, get_existing_commit
from ingestion.models import Chunk

COMMIT_FILE = 'COMMIT_SHA'

def run():
    print("[bold cyan]Ingestion start[/bold cyan]")
    ensure_index()

    for mod_name, version, prefix in list_module_versions():
        print(f"\\n[bold]Module[/bold] {mod_name}  [bold]Version[/bold] {version}")
        commit_sha = None
        files = list(iter_files(prefix))

        # get commit sha first
        for key in files:
            if key.endswith(COMMIT_FILE):
                commit_sha = read_s3(key).strip()
                break
        commit_sha = commit_sha or version

        all_chunks: list[Chunk] = []
        for key in files:
            if key.endswith(COMMIT_FILE): continue
            # Idempotency shortcut: if commit sha unchanged for this path, skip reindex
            existing = get_existing_commit(mod_name, version, key)
            if existing and existing == commit_sha:
                continue
            all_chunks.extend(parse_module_file(mod_name, version, key, commit_sha))

        if not all_chunks:
            print("[yellow]Nothing to update[/yellow]")
            continue
        print(f"DEBUG: Found {len(all_chunks)} chunks to update")

        all_chunks = enrich(all_chunks, mod_name, version)
        all_chunks = enforce_size(all_chunks, settings.embed_max_chars)

        # embed (code + text concatenated)
        for c in all_chunks:
            combined = "\\n\\n".join(filter(None, [c.text_context, c.code_normalized]))
            if combined:
                c.embedding = embed_text(combined)

        # 🐛 ADD THIS LOGGING STATEMENT
        print("--- First chunk object ---")
        print(all_chunks[0].__dict__)
        print(f"DEBUG: Chunk object before sending to OpenSearch:\n{all_chunks[0].__dict__}")

        # bulk index in AOSS, batches of 500
        batch, total = [], 0
        for c in all_chunks:
            print(c.dict())
            if not c.embedding: continue
            batch.append(c)
            if len(batch) >= settings.aoss_bulk_size:
                ok, _ = bulk_index(batch)
                total += ok
                batch = []
        if batch:
            ok, _ = bulk_index(batch)
            total += ok
        print(f"[green]Indexed {total} docs[/green]")

        # upsert denormalized catalog rows in DDB (per path)
        seen = set()
        for c in all_chunks:
            key = f"{c.module_name}|{c.version}|{c.path}"
            if key in seen: continue
            seen.add(key)
            doc = {
                "pk": f"MOD#{c.module_name}",
                "sk": f"VER#{c.version}#PATH#{c.path}",
                "module_name": c.module_name,
                "version": c.version,
                "path": c.path,
                "commit_sha": c.commit_sha,
                "inputs": sorted({i for cc in all_chunks if cc.path==c.path for i in cc.inputs}),
                "outputs": sorted({o for cc in all_chunks if cc.path==c.path for o in cc.outputs}),
                "services": sorted({s for cc in all_chunks if cc.path==c.path for s in cc.services}),
                "stable": True,
            }
            upsert_catalog(doc)

if __name__ == "__main__":
    run()

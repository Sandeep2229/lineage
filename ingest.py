"""Ingest Nimbus docs + hand-verified graph into HydraDB. Run ONCE, then freeze.
Run: python build_graph.py && python ingest.py
"""
import io, json, os, re, time
from pathlib import Path
from dotenv import load_dotenv
from hydra_db import HydraDB
from hydra_db.errors import ConflictError

load_dotenv()
client = HydraDB(token=os.environ["HYDRA_DB_API_KEY"])
DB = os.getenv("LINEAGE_DB", "lineage_demo")
COL = "nimbus_kb"

def meta_from(text):
    m = {}
    for key in ("Date", "Opened", "Decided by", "Author", "Status", "Service"):
        hit = re.search(rf"^{key}:\s*(.+)$", text, re.M)
        if hit:
            m[key.lower().replace(" ", "_")] = hit.group(1).strip()
    title = text.splitlines()[0].lstrip("# ").strip()
    m["title"] = title
    return m

try:
    client.databases.create(database=DB)
except ConflictError:
    print(f"{DB} exists, reusing")
while not client.databases.status(database=DB).data.infra.ready_for_ingestion:
    print("Provisioning..."); time.sleep(3)

ids = []
for path in sorted(Path("data").glob("*.md")):
    doc_id = path.stem
    text = path.read_text()
    kwargs = dict(
        database=DB, collection=COL, type="knowledge",
        documents=[(path.name, io.BytesIO(text.encode()), "text/plain")],
        document_metadata=json.dumps([{"id": doc_id, "additional_metadata": meta_from(text)}]),
        upsert="true",
    )
    gpath = Path("graph") / f"{doc_id}.json"
    if gpath.exists():
        kwargs["graph_payload"] = json.dumps({doc_id: json.loads(gpath.read_text())})
    try:
        r = client.context.ingest(**kwargs)
        ids.extend(x.id for x in r.data.results)
        print(f"OK   {doc_id}" + ("  (+graph)" if gpath.exists() else ""))
    except Exception as e:
        print(f"FAIL {doc_id}: {e}")

print(f"\nWaiting for {len(ids)} sources to finish indexing...")
while True:
    st = client.context.status(database=DB, collection=COL, ids=ids)
    states = {i: s.indexing_status for i, s in zip(ids, st.data.statuses)}
    done = sum(v == "completed" for v in states.values())
    print(f"  {done}/{len(ids)} completed", {k: v for k, v in states.items() if v != "completed"})
    if done == len(ids):
        break
    if any(v in ("errored", "failed") for v in states.values()):
        raise SystemExit(f"Indexing failed: {states}")
    time.sleep(8)
print("All indexed. Database is frozen; do not re-run before the demo.")

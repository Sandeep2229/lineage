import os, io, json, time
from dotenv import load_dotenv
from hydra_db import HydraDB
from hydra_db.errors import ConflictError

load_dotenv()
client = HydraDB(token=os.environ["HYDRA_DB_API_KEY"])
DB, COL = "lineage_dev", "nimbus_kb"

# 1. Create the database
try:
    client.databases.create(database=DB)
except ConflictError:
    print("Database exists, reusing")
while not client.databases.status(database=DB).data.infra.ready_for_ingestion:
    print("Provisioning..."); time.sleep(3)
print("Database ready")

# 2. Ingest one document
doc = "ADR-001: Use Postgres. Status: Accepted. Date: 2026-03-01. Decided by Priya. Postgres is our primary datastore for the orders service."
r = client.context.ingest(
    database=DB, collection=COL, type="knowledge",
    documents=("adr_001.md", io.BytesIO(doc.encode()), "text/plain"),
    document_metadata=json.dumps([{"id": "adr_001", "additional_metadata": {"title": "ADR-001: Use Postgres", "doc_type": "adr"}}]),
    upsert="true",
)
ids = [x.id for x in r.data.results]
print("Ingested:", ids)

# 3. Wait for indexing
while True:
    st = client.context.status(database=DB, collection=COL, ids=ids)
    states = [s.indexing_status for s in st.data.statuses]
    print("Status:", states)
    if all(s == "completed" for s in states): break
    if any(s in ("errored", "failed") for s in states): raise SystemExit(states)
    time.sleep(5)

# 4. Query
res = client.query(
    database=DB, collection=COL, query="Which database did we choose and who decided?",
    type="knowledge", query_by="hybrid", mode="fast", max_results=5, graph_context=True,
)
for c in res.data.chunks or []:
    print("\n", c.source_title, "->", (c.chunk_content or "")[:200])
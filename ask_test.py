"""Compare graph ON vs OFF for one question. Run: python ask_test.py "Why did we move off Postgres?"
"""
import os, sys
from dotenv import load_dotenv
from hydra_db import HydraDB

load_dotenv()
client = HydraDB(token=os.environ["HYDRA_DB_API_KEY"])
DB = os.getenv("LINEAGE_DB", "lineage_demo")
q = sys.argv[1] if len(sys.argv) > 1 else "Why did we move orders-service off Postgres?"

def f(o, k, d=""):
    if o is None: return d
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)

for graph in (False, True):
    res = client.query(database=DB, collection="nimbus_kb", query=q, type="knowledge",
                       query_by="hybrid", mode="thinking" if graph else "fast",
                       max_results=8, graph_context=graph)
    print("\n" + "=" * 60, f"\nGRAPH {'ON' if graph else 'OFF'}")
    for c in res.data.chunks or []:
        print(" -", c.source_title or c.id)
    g = res.data.graph_context
    for p in (f(g, "query_paths", []) or []):
        hops = [f"{f(t.source,'name')} --{f(t.relation,'canonical_predicate')}--> {f(t.target,'name')}"
                for t in (p.triplets or [])]
        print("  PATH:", " | ".join(hops))

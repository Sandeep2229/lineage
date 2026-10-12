"""Lineage API. Run: uvicorn app:app --reload --port 8000   then open http://localhost:8000
Works with OPENAI_API_KEY or ANTHROPIC_API_KEY in .env (Anthropic preferred if both).
"""
import asyncio, json, os, re
from pathlib import Path
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from hydra_db import HydraDB
from hydra_db.helpers import build_string

load_dotenv()
client = HydraDB(token=os.environ["HYDRA_DB_API_KEY"])
DB = os.getenv("LINEAGE_DB", "lineage_demo")
COL = "nimbus_kb"
DECISIONS = json.loads(Path("decisions.json").read_text())
DOCS = {p.stem: p.read_text() for p in Path("data").glob("*.md")}
app = FastAPI(title="Lineage")
CACHE: dict = {}

# ---------- LLM (Anthropic or OpenAI, plain HTTP) ----------
def llm(system: str, user: str) -> str:
    if os.getenv("ANTHROPIC_API_KEY"):
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
            json={"model": os.getenv("LLM_MODEL", "claude-sonnet-5-5"), "max_tokens": 1200,
                  "system": system, "messages": [{"role": "user", "content": user}]})
        r.raise_for_status()
        return r.json()["content"][0]["text"]
    if os.getenv("OPENAI_API_KEY"):
        r = httpx.post("https://api.openai.com/v1/chat/completions", timeout=60, headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": os.getenv("LLM_MODEL", "gpt-4o"),
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    return ""

def parse_json(text: str):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except Exception:
        return None

# ---------- HydraDB ----------
def f(o, k, d=""):
    if o is None: return d
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)

def hydra(q: str, graph: bool):
    return client.query(database=DB, collection=COL, query=q, type="knowledge", query_by="hybrid",
                        mode="thinking" if graph else "fast", max_results=8, graph_context=graph)

def chunks_of(res):
    return [{"source": c.source_title or c.id, "text": (c.chunk_content or "")[:280]}
            for c in (res.data.chunks or [])]

def paths_of(res):
    out, seen = [], set()
    for p in (f(res.data.graph_context, "query_paths", []) or []):
        hops = [{"from": f(t.source, "name"), "edge": f(t.relation, "canonical_predicate"),
                 "to": f(t.target, "name")} for t in (p.triplets or [])]
        key = json.dumps(hops)
        if hops and key not in seen:
            seen.add(key); out.append(hops)
    return out

# ---------- /ask ----------
ASK_SYS = ("You are Lineage, a company brain that tracks how decisions change over time. "
           "Answer ONLY from the context. Prefer ACTIVE decisions; when a decision was superseded, say so "
           "and explain the chain (what happened, why it changed, who decided, when). "
           "Cite the source file in brackets after every claim, like [adr_007.md]. Be concise: 4 to 7 sentences.")

@app.get("/api/ask")
async def ask(q: str):
    if q in CACHE:
        return CACHE[q]
    g_on, g_off = await asyncio.gather(asyncio.to_thread(hydra, q, True), asyncio.to_thread(hydra, q, False))
    ctx = build_string(g_on)
    answer = await asyncio.to_thread(llm, ASK_SYS, f"Context:\n{ctx}\n\nQuestion: {q}")
    out = {"question": q, "answer": answer or "(No LLM key set; showing retrieval only.)",
           "paths": paths_of(g_on), "graph_chunks": chunks_of(g_on), "baseline_chunks": chunks_of(g_off)}
    CACHE[q] = out
    return out

# ---------- /check (contradiction radar) ----------
class CheckIn(BaseModel):
    text: str

CHECK_SYS = ("You are a contradiction detector for a company brain. You get a NEW piece of work "
             "(PR, draft, message), the list of company decisions with status, and retrieved context. "
             "Decide whether the new work conflicts with any ACTIVE decision, or relies on a SUPERSEDED one. "
             'Reply with JSON only: {"conflict": true|false, "decision_id": "...", "superseded_id": "... or null", '
             '"severity": "high|medium|low", "explanation": "2 sentences", "evidence": ["file.md", ...], '
             '"suggested_fix": "1 sentence"}')

def heuristic(text: str):
    t = text.lower()
    if "postgres" in t and "order" in t:
        return {"conflict": True, "decision_id": "adr_007", "superseded_id": "adr_001", "severity": "high",
                "explanation": "This adds Postgres storage to orders-service, but ADR-007 (2026-09-03) moved orders-service "
                               "to DynamoDB and banned new Postgres tables. It relies on ADR-001, which is superseded.",
                "evidence": ["adr_007.md", "meeting_arch_0702.md", "adr_001.md"],
                "suggested_fix": "Write the audit records to a DynamoDB table instead."}
    if "$49" in t or "49 per seat" in t:
        return {"conflict": True, "decision_id": "price_39", "superseded_id": "price_49", "severity": "medium",
                "explanation": "This shows the retired $49 price. Since 2026-09-01 the Pro plan is $39 plus usage, "
                               "and all public pages must show $39.",
                "evidence": ["pricing_decision_0901.md", "pricing_memo_0405.md"],
                "suggested_fix": "Change the price to $39 per seat plus usage."}
    return {"conflict": False, "decision_id": None, "superseded_id": None, "severity": "low",
            "explanation": "No conflict with active decisions found.", "evidence": [], "suggested_fix": ""}

@app.post("/api/check")
async def check(body: CheckIn):
    res = await asyncio.to_thread(hydra, body.text, True)
    ledger = json.dumps(DECISIONS, indent=1)
    raw = await asyncio.to_thread(
        llm, CHECK_SYS, f"DECISIONS:\n{ledger}\n\nRETRIEVED CONTEXT:\n{build_string(res)}\n\nNEW WORK:\n{body.text}")
    verdict = parse_json(raw) or heuristic(body.text)
    by_id = {d["id"]: d for d in DECISIONS}
    verdict["decision"] = by_id.get(verdict.get("decision_id"))
    verdict["trail"] = [{"doc": d, "title": DOCS.get(d, "").splitlines()[0].lstrip("# ")}
                        for d in (verdict["decision"] or {}).get("trail", [])]
    verdict["paths"] = paths_of(res)
    return verdict

@app.get("/api/eval")
def eval_results():
    p = Path("eval_results.json")
    if not p.exists():
        return {}
    d = json.loads(p.read_text())
    return {"on": d["on"], "off": d["off"], "n": d["n"]}

@app.get("/api/decisions")
def decisions():
    return DECISIONS

@app.get("/api/doc/{doc_id}")
def doc(doc_id: str):
    return {"id": doc_id, "text": DOCS.get(doc_id.replace(".md", ""), "Not found")}

@app.get("/")
def index():
    return FileResponse("index.html")

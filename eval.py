"""Graph ON vs OFF eval. Same LLM, same prompt, only the retrieval differs.
Run: python eval.py   -> prints a table and writes eval_results.json (shown in the UI)
"""
import json, time
from app import hydra, llm, ASK_SYS, build_string

QS = [
    ("Why did orders-service move off Postgres?", ["INC-042", "DynamoDB"]),
    ("Who owns the orders-service migration and when is it due?", ["Marcus", "Q4"]),
    ("What is the current price of the Pro plan?", ["39"]),
    ("Which incident led to the decision that superseded ADR-001?", ["INC-042"]),
    ("Who made the decision that replaced the original Pro pricing?", ["Ana"]),
    ("Is PR #318 consistent with current architecture decisions? Which decision applies?", ["ADR-007"]),
    ("Who was on-call during the incident that motivated ADR-007?", ["James"]),
    ("Which service stays on Postgres after the migration decision?", ["billing"]),
    ("Is the price on the landing page draft correct? What should it be?", ["39"]),
    ("Who first proposed DynamoDB, and in which channel?", ["Priya", "infra"]),
]

def run(graph: bool):
    rows = []
    for q, must in QS:
        res = hydra(q, graph)
        ans = llm(ASK_SYS, f"Context:\n{build_string(res)}\n\nQuestion: {q}")
        ok = all(m.lower() in ans.lower() for m in must)
        rows.append({"q": q, "must": must, "pass": ok, "answer": ans})
        print(f"  [{'PASS' if ok else 'FAIL'}] {q}")
        time.sleep(0.3)
    return rows

if __name__ == "__main__":
    print("GRAPH ON"); on = run(True)
    print("GRAPH OFF"); off = run(False)
    s_on, s_off = sum(r["pass"] for r in on), sum(r["pass"] for r in off)
    print(f"\nScore  graph ON: {s_on}/{len(QS)}   graph OFF: {s_off}/{len(QS)}")
    json.dump({"on": s_on, "off": s_off, "n": len(QS), "graph_on": on, "graph_off": off},
              open("eval_results.json", "w"), indent=2)
    print("Wrote eval_results.json")

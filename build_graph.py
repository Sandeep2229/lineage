"""Hand-verified decision graph for the Nimbus demo.
Writes graph/<doc_id>.json (HydraDB graph_payload per document) and decisions.json (decision ledger).
Run: python build_graph.py
"""
import json
from pathlib import Path

E = {
    # decisions
    "adr_001": {"name": "ADR-001 Use Postgres", "type": "DECISION", "namespace": "decisions"},
    "adr_007": {"name": "ADR-007 Migrate orders to DynamoDB", "type": "DECISION", "namespace": "decisions"},
    "arch_rule": {"name": "No new Postgres tables for orders-service", "type": "DECISION", "namespace": "decisions"},
    "price_49": {"name": "Pro plan $49 flat", "type": "DECISION", "namespace": "decisions"},
    "price_39": {"name": "Pro plan $39 plus usage", "type": "DECISION", "namespace": "decisions"},
    # people
    "priya": {"name": "Priya Shah", "type": "PERSON", "namespace": "people"},
    "marcus": {"name": "Marcus Lee", "type": "PERSON", "namespace": "people"},
    "james": {"name": "James Okafor", "type": "PERSON", "namespace": "people"},
    "dev": {"name": "Dev Raman", "type": "PERSON", "namespace": "people"},
    "ana": {"name": "Ana Torres", "type": "PERSON", "namespace": "people"},
    "kenji": {"name": "Kenji Mori", "type": "PERSON", "namespace": "people"},
    "lena": {"name": "Lena Park", "type": "PERSON", "namespace": "people"},
    # systems
    "orders": {"name": "orders-service", "type": "SERVICE", "namespace": "services"},
    "billing": {"name": "billing-service", "type": "SERVICE", "namespace": "services"},
    "postgres": {"name": "Postgres", "type": "TECHNOLOGY", "namespace": "tech"},
    "dynamo": {"name": "DynamoDB", "type": "TECHNOLOGY", "namespace": "tech"},
    "pro_plan": {"name": "Pro plan", "type": "PRODUCT", "namespace": "products"},
    # events and artifacts
    "inc_042": {"name": "INC-042 Orders write bottleneck", "type": "INCIDENT", "namespace": "incidents"},
    "slack_infra": {"name": "Slack #infra thread 2026-06-20", "type": "DISCUSSION", "namespace": "discussions"},
    "arch_review": {"name": "Architecture Review 2026-07-02", "type": "MEETING", "namespace": "meetings"},
    "sales_thread": {"name": "Slack #sales thread 2026-08-15", "type": "DISCUSSION", "namespace": "discussions"},
    "pr_318": {"name": "PR #318 Add orders_audit Postgres table", "type": "CHANGE", "namespace": "changes"},
    "mkt_draft": {"name": "Landing page draft Pro plan", "type": "CHANGE", "namespace": "changes"},
}

def rel(s, p, t, ctx=""):
    r = {"source": s, "target": t, "predicate": p}
    if ctx:
        r["context"] = ctx
    return r

# relations grouped by the document that evidences them
DOC_RELS = {
    "adr_001": [
        rel("adr_001", "DECIDED_BY", "priya", "Priya Shah decided ADR-001 on 2026-03-01."),
        rel("adr_001", "CHOOSES", "postgres", "ADR-001 chose Postgres as primary datastore."),
        rel("adr_001", "AFFECTS", "orders", "ADR-001 put orders-service on Postgres."),
        rel("adr_001", "AFFECTS", "billing", "ADR-001 put billing-service on Postgres."),
    ],
    "inc_042": [
        rel("inc_042", "CAUSED_BY", "adr_001", "INC-042 root cause: ADR-001 single Postgres primary cannot absorb burst writes."),
        rel("inc_042", "AFFECTS", "orders", "INC-042 broke checkout in orders-service for 38 minutes on 2026-06-12."),
        rel("james", "RESPONDED_TO", "inc_042", "James Okafor was on-call for INC-042."),
    ],
    "slack_infra_0620": [
        rel("slack_infra", "MOTIVATED_BY", "inc_042", "The #infra debate on 2026-06-20 followed INC-042."),
        rel("priya", "PROPOSED_IN", "slack_infra", "Priya proposed moving orders-service to DynamoDB."),
        rel("marcus", "DISCUSSED_IN", "slack_infra", "Marcus raised cost and join concerns."),
        rel("james", "DISCUSSED_IN", "slack_infra", "James supported DynamoDB from the SRE side."),
    ],
    "meeting_arch_0702": [
        rel("arch_rule", "DECIDED_IN", "arch_review", "Arch review on 2026-07-02 ruled no new Postgres tables for orders-service."),
        rel("arch_review", "FOLLOWS", "slack_infra", "The arch review settled the #infra debate."),
        rel("marcus", "OWNS", "adr_007", "Marcus Lee owns the DynamoDB migration, due end of Q4 2026."),
        rel("arch_rule", "AFFECTS", "orders", "Rule applies to orders-service."),
    ],
    "adr_007": [
        rel("adr_007", "SUPERSEDES", "adr_001", "ADR-007 (2026-09-03) supersedes ADR-001 for orders-service only."),
        rel("adr_007", "MOTIVATED_BY", "inc_042", "ADR-007 was motivated by INC-042."),
        rel("adr_007", "DECIDED_BY", "priya", "Priya Shah wrote ADR-007."),
        rel("adr_007", "CHOOSES", "dynamo", "ADR-007 moves orders-service to DynamoDB."),
        rel("adr_007", "AFFECTS", "orders", "ADR-007 applies to orders-service."),
        rel("adr_007", "FORMALIZES", "arch_rule", "ADR-007 formalizes the arch review rule."),
    ],
    "pr_318": [
        rel("dev", "AUTHORED", "pr_318", "Dev Raman opened PR #318 on 2026-10-10."),
        rel("pr_318", "AFFECTS", "orders", "PR #318 changes orders-service."),
        rel("pr_318", "USES", "postgres", "PR #318 adds a new Postgres table orders_audit."),
    ],
    "pricing_memo_0405": [
        rel("price_49", "DECIDED_BY", "ana", "Ana Torres set Pro at $49 flat on 2026-04-05."),
        rel("price_49", "AFFECTS", "pro_plan", "Pricing for the Pro plan."),
    ],
    "slack_sales_0815": [
        rel("sales_thread", "CRITIQUES", "price_49", "Sales lost deals because $49 flat was too high."),
        rel("kenji", "DISCUSSED_IN", "sales_thread", "Kenji Mori reported lost deals."),
    ],
    "pricing_decision_0901": [
        rel("price_39", "SUPERSEDES", "price_49", "On 2026-09-01 Pro moved to $39 plus usage; $49 retired."),
        rel("price_39", "MOTIVATED_BY", "sales_thread", "Motivated by August churn feedback."),
        rel("price_39", "DECIDED_BY", "ana", "Ana Torres decided the new price."),
        rel("price_39", "AFFECTS", "pro_plan", "Pricing for the Pro plan."),
    ],
    "marketing_draft_1008": [
        rel("lena", "AUTHORED", "mkt_draft", "Lena Park drafted the landing page on 2026-10-08."),
        rel("mkt_draft", "AFFECTS", "pro_plan", "Landing page advertises the Pro plan at $49."),
    ],
    "hiring_plan": [
        rel("marcus", "LEADS", "orders", "Marcus Lee leads the orders-service migration team."),
    ],
}

# decision ledger used by the contradiction radar
DECISIONS = [
    {"id": "adr_001", "title": "ADR-001 Use Postgres", "status": "superseded", "superseded_by": "adr_007",
     "scope": "orders-service", "date": "2026-03-01", "doc": "adr_001"},
    {"id": "adr_007", "title": "ADR-007 Migrate orders-service to DynamoDB; no new Postgres tables for orders-service",
     "status": "active", "scope": "orders-service", "date": "2026-09-03", "doc": "adr_007",
     "trail": ["adr_001", "inc_042", "slack_infra_0620", "meeting_arch_0702", "adr_007"]},
    {"id": "price_49", "title": "Pro plan $49 flat", "status": "superseded", "superseded_by": "price_39",
     "scope": "Pro plan pricing", "date": "2026-04-05", "doc": "pricing_memo_0405"},
    {"id": "price_39", "title": "Pro plan $39 per seat plus usage; all public pages must show $39",
     "status": "active", "scope": "Pro plan pricing", "date": "2026-09-01", "doc": "pricing_decision_0901",
     "trail": ["pricing_memo_0405", "slack_sales_0815", "pricing_decision_0901"]},
]

if __name__ == "__main__":
    out = Path("graph"); out.mkdir(exist_ok=True)
    for doc_id, rels in DOC_RELS.items():
        keys = {k for r in rels for k in (r["source"], r["target"])}
        payload = {"entities": {k: E[k] for k in sorted(keys)}, "relations": rels}
        (out / f"{doc_id}.json").write_text(json.dumps(payload, indent=2))
    Path("decisions.json").write_text(json.dumps(DECISIONS, indent=2))
    print(f"Wrote {len(DOC_RELS)} graph files and decisions.json")

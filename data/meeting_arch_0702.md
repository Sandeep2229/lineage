# Architecture Review Meeting Notes, 2026-07-02
Attendees: Priya Shah, Marcus Lee, James Okafor, Dev Raman

Decision: orders-service will migrate from Postgres to DynamoDB. billing-service stays on Postgres.
Owner of the migration: Marcus Lee.
Deadline: end of Q4 2026.
Rule going forward: no new Postgres tables for orders-service. All new order data goes to DynamoDB.
Priya will write ADR-007 to formalize this.

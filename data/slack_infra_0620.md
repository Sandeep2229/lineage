# Slack #infra thread, 2026-06-20

Priya Shah: Following INC-042, I propose moving orders-service to DynamoDB. On-demand capacity handles burst writes without a single primary.
Marcus Lee: Worried about cost and losing joins. Billing reports join orders with invoices.
James Okafor: From the SRE side, DynamoDB removes the single point of failure that caused INC-042. I support it.
Priya Shah: Billing can stay on Postgres for now. Only orders-service moves. Let's decide at the July arch review.

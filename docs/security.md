# Security design

## Security groups

Traffic is scoped tier-to-tier — nothing is open more broadly than the tier immediately in front of it needs.

### `alb-sg` (attached to the ALB)

| Direction | Protocol | Port | Source/Destination | Purpose |
|---|---|---|---|---|
| Inbound | TCP | 443 | `0.0.0.0/0` | Public HTTPS traffic |
| Inbound | TCP | 80 | `0.0.0.0/0` | Redirected to 443 at the listener |
| Outbound | TCP | 8080 | `app-sg` | Forward to application instances |

### `app-sg` (attached to EC2 instances in the Auto Scaling group)

| Direction | Protocol | Port | Source/Destination | Purpose |
|---|---|---|---|---|
| Inbound | TCP | 8080 | `alb-sg` | Only the ALB can reach the app — not the internet, not other instances |
| Outbound | TCP | 3306/5432 | `db-sg` | Database traffic |
| Outbound | TCP | 443 | `0.0.0.0/0` (via NAT) | OS/package updates, calls to AWS APIs (SSM, CloudWatch) |

### `db-sg` (attached to the RDS instance)

| Direction | Protocol | Port | Source/Destination | Purpose |
|---|---|---|---|---|
| Inbound | TCP | 3306 or 5432 | `app-sg` | Only application instances can reach the database — no direct internet or bastion access |

No security group in this design allows inbound SSH (port 22) from anywhere. All instance access goes through Systems Manager Session Manager instead.

## Network ACLs

Security groups are stateful and handle most access control here. NACLs are left at their default (allow all within the VPC) unless you have a specific requirement to add a subnet-level deny rule — for example, explicitly blocking a known-bad CIDR range as a second layer of defense, since NACLs evaluate before traffic reaches the security group.

## IAM

- The EC2 instance profile grants only `AmazonSSMManagedInstanceCore` (for Session Manager) plus whatever least-privilege permissions the application itself needs (e.g. reading a specific Secrets Manager secret for the database password, if you wire the app up to RDS).
- No IAM user access keys are used anywhere in this project — all access is role-based.

## No inbound SSH, no bastion host

Traditional designs put a bastion host in the public subnet with SSH open to a corporate IP range. This project uses **AWS Systems Manager Session Manager** instead:

- No inbound ports need to be opened on instances for administrative access.
- No SSH key pairs to generate, distribute, or rotate.
- Every session is logged and can be sent to CloudWatch Logs or S3 for audit purposes.
- Access is controlled entirely through IAM policy, so it's revoked the same way any other AWS permission is revoked.

## WAF

See `waf/owasp-managed-rules.md`. The Web ACL sits in front of the ALB and filters malicious requests (SQL injection, XSS, known bad inputs, reputation-listed IPs) before they reach the application tier.

## Secrets

This demo application doesn't yet connect to the database, so no credentials are hardcoded anywhere. If you extend it to use RDS, store the database credentials in **AWS Secrets Manager** with automatic rotation enabled, and grant the EC2 instance role permission to read that specific secret — never place credentials in the user-data script, environment variables baked into the AMI, or application code.

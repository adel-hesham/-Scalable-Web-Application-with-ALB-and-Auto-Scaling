# -Scalable-Web-Application-with-ALB-and-Auto-Scaling

A production-grade, highly available web application deployed on AWS: EC2 instances in an Auto Scaling group behind an Application Load Balancer, a CloudFront distribution for edge caching, and a Multi-AZ RDS backend — all inside a purpose-built VPC spanning two Availability Zones.

This repository is deployed manually through the AWS Console/CLI (no Terraform or CloudFormation) — see `docs/deployment-guide.md` for the exact steps.

## Architecture diagram



## Architecture flow

1. A request resolves through **Route 53**, which also runs a health check against the application endpoint.
2. **CloudFront** serves cached static assets (`/static/*`) from edge locations and forwards everything else toward the origin.
3. **AWS WAF**, attached to the **Application Load Balancer**, filters requests against OWASP Top 10 rule sets before they reach the application.
4. The ALB performs Layer 7 routing and health-checks (`/health`) across instances in **two Availability Zones**.
5. The app runs in **private subnets** inside an **Auto Scaling group**, launched from a shared Launch Template, scaling on a CPU target-tracking policy.
6. The application tier can read/write a **Multi-AZ RDS** instance — the primary sits in one AZ, with a synchronously replicated standby in the second AZ that takes over automatically on failure.
7. **CloudWatch** collects metrics from every tier; **SNS** delivers alarm notifications.
8. **Systems Manager Session Manager** provides secure, auditable shell access — no SSH keys, no bastion host, no open inbound ports.

## Repository structure

```
.
├── README.md
├── LICENSE
├── architecture-diagram.png
├── app/                        # The application itself
│   ├── app.py                  # Flask app: "/" demo page + "/health" for the ALB
│   ├── requirements.txt
│   ├── templates/index.html
│   └── static/style.css
├── deploy/                     # EC2 Launch Template bootstrap
│   ├── user-data.sh
│   └── webapp.service          # systemd unit run by user-data.sh
├── waf/
│   └── owasp-managed-rules.md  # Managed rule groups + rate limiting to attach to the Web ACL
├── monitoring/
│   ├── cloudwatch-dashboard.json
│   └── cloudwatch-alarms.md
└── docs/
    ├── deployment-guide.md     # Full manual build order, VPC → Route 53
    ├── security.md             # Security group rules, IAM, no-SSH access model
    └── runbook.md              # What to do when each alarm fires
```

## Running the app locally

```bash
cd app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:8080`. Outside of EC2 there's no instance metadata service to query, so the page will show `local-dev` / `unknown` for the instance ID and AZ — that's expected, and confirms the fallback path works.

## Deploying to AWS

Follow `docs/deployment-guide.md` from start to finish. It builds, in order: the VPC and subnets, security groups, RDS Multi-AZ instance, EC2 Launch Template, Auto Scaling group, ALB + target group, WAF Web ACL, Systems Manager access, CloudFront distribution, Route 53 record, and CloudWatch alarms/dashboard.

Before creating the Launch Template, edit `deploy/user-data.sh` and replace `REPO_URL` with this repository's actual URL, so each new instance can pull the app on boot.

## AWS services used

| Service | Purpose |
|---|---|
| Amazon VPC | Public/private subnets across 2 AZs, NAT Gateways, Security Groups, NACLs |
| Amazon EC2 + Auto Scaling | Application compute, Launch Template, target-tracking scaling policy |
| Application Load Balancer + AWS WAF | Layer 7 routing, health checks, OWASP Top 10 protection |
| Amazon CloudFront | Edge caching for static assets, reduced latency for global users |
| Amazon RDS (Multi-AZ) | MySQL/PostgreSQL with automated failover |
| Amazon Route 53 | DNS, alias record, health checks |
| AWS Systems Manager | Session Manager for secure, agent-based instance access |
| Amazon CloudWatch + SNS | Dashboards, alarms, and operational notifications |

## Key design decisions

- **Private-only compute and data.** EC2 instances and the RDS instance have no public IPs or inbound internet routes. All admin access goes through Session Manager; all outbound internet access goes through NAT Gateways.
- **Defense in depth.** Security groups scope access tier-to-tier (ALB → EC2 → RDS only); WAF filters malicious traffic before it reaches the ALB. See `docs/security.md` for the full rule set.
- **Stateless application tier.** EC2 instances hold no session state, so the Auto Scaling group can freely launch, terminate, and replace instances without disrupting active users.
- **Managed failover over custom scripts.** RDS Multi-AZ handles database failover natively — there's no custom replication or failover logic to maintain.
- **No SSH, no bastion host.** Systems Manager Session Manager replaces the traditional bastion pattern entirely.

## Monitoring and operations

- `monitoring/cloudwatch-alarms.md` — the alarms to create and what they watch for.
- `monitoring/cloudwatch-dashboard.json` — importable CloudWatch dashboard covering ALB, ASG, and RDS metrics.
- `docs/runbook.md` — what to actually do when each alarm fires.

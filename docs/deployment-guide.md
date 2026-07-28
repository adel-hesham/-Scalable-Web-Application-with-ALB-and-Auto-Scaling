# Deployment guide

This project is deployed manually through the AWS Management Console (or
equivalent AWS CLI commands) rather than with Terraform/CloudFormation.
Follow these steps in order — later steps depend on resources created in
earlier ones.

## 1. VPC and networking

1. **VPC** → **Create VPC** → select "VPC and more" to get subnets, route tables, and an Internet Gateway generated together.
   - IPv4 CIDR: `10.0.0.0/16`
   - Number of Availability Zones: **2**
   - Public subnets: **2** (e.g. `10.0.0.0/24`, `10.0.1.0/24`)
   - Private subnets: **2** (e.g. `10.0.2.0/24`, `10.0.3.0/24`)
   - NAT gateways: **1 per AZ** (for full Multi-AZ resilience)
2. Add a third pair of "database" private subnets (e.g. `10.0.4.0/24`, `10.0.5.0/24`) for RDS, isolated from the application subnets.
3. Confirm the private subnet route tables point outbound (`0.0.0.0/0`) traffic to the NAT Gateway in the same AZ, and public subnet route tables point to the Internet Gateway.

## 2. Security groups

Create three security groups (see `docs/security.md` for the full rule tables):

- `alb-sg` — allows inbound 443/80 from the internet
- `app-sg` — allows inbound 8080 from `alb-sg` only
- `db-sg` — allows inbound 3306 (MySQL) or 5432 (PostgreSQL) from `app-sg` only

## 3. RDS Multi-AZ

1. **RDS** → **Create database** → Standard create.
2. Engine: MySQL or PostgreSQL (match your application).
3. Templates: **Production**.
4. Availability: **Multi-AZ DB instance**.
5. DB subnet group: create one using the two "database" private subnets.
6. VPC security group: `db-sg`.
7. Enable automated backups and note the endpoint once available — the application doesn't currently use the database, but the endpoint is where you'd wire it in.

## 4. Launch Template

1. **EC2** → **Launch Templates** → **Create launch template**.
2. AMI: latest **Amazon Linux 2023**.
3. Instance type: `t3.micro` (adjust for real load).
4. Key pair: none required — access is via Systems Manager Session Manager (see step 8).
5. Security group: `app-sg`.
6. IAM instance profile: create/attach a role with the `AmazonSSMManagedInstanceCore` managed policy (required for Session Manager).
7. User data: paste the contents of `deploy/user-data.sh`, replacing `REPO_URL` with this repository's URL.

## 5. Auto Scaling group

1. **EC2** → **Auto Scaling Groups** → **Create Auto Scaling group**, using the Launch Template from step 4.
2. VPC subnets: select **both private application subnets** (one per AZ).
3. Attach to a new load balancer target group later (step 6), or skip and attach after the ALB exists.
4. Group size: min 2, desired 2, max 6 (adjust to expected load).
5. Scaling policy: **Target tracking** on `ASGAverageCPUUtilization`, target value **50%** (the project brief calls for headroom around 40-50% depending on your workload).

## 6. Application Load Balancer + target group

1. **EC2** → **Target Groups** → **Create target group**.
   - Target type: Instances (or "Auto Scaling group" if creating inline)
   - Protocol/port: HTTP / 8080
   - Health check path: `/health`
2. **EC2** → **Load Balancers** → **Create Application Load Balancer**.
   - Scheme: internet-facing
   - Subnets: both public subnets
   - Security group: `alb-sg`
   - Listener: HTTPS 443 (attach an ACM certificate) — redirect HTTP 80 to HTTPS
   - Forward to the target group from step 1
3. Go back to the Auto Scaling group and attach it to this target group if not already linked.

## 7. AWS WAF

Follow `waf/owasp-managed-rules.md` to create the Web ACL and associate it with the ALB.

## 8. Systems Manager access

Confirm the IAM instance profile from step 4 has `AmazonSSMManagedInstanceCore`. Once instances are running, connect via:

```
aws ssm start-session --target <instance-id>
```

No SSH keys, bastion host, or open port 22 required.

## 9. CloudFront

1. **CloudFront** → **Create distribution**.
2. Origin domain: the ALB's DNS name.
3. Viewer protocol policy: Redirect HTTP to HTTPS.
4. Cache policy: use `CachingOptimized` for the `/static/*` path pattern; use `CachingDisabled` for `/` and `/health` so dynamic content and health checks always reach the origin.
5. Attach the ACM certificate (must be in `us-east-1` for CloudFront) and set the alternate domain name (CNAME) to your custom domain.

## 10. Route 53

1. **Route 53** → **Hosted zones** → select your domain.
2. Create an **A record**, type **Alias**, targeting the CloudFront distribution from step 9.
3. Optionally create a **health check** against `https://<your-domain>/health` and reference it from a failover routing policy if you later add a secondary Region.

## 11. Monitoring

Follow `monitoring/cloudwatch-alarms.md` to create the SNS topic and alarms, and import `monitoring/cloudwatch-dashboard.json` as a CloudWatch dashboard.

## Teardown order

When tearing this down, reverse the order above: CloudFront distribution (disable, then delete) → Route 53 records → ALB + target group → Auto Scaling group (this terminates instances) → Launch Template → RDS instance (skip final snapshot only for throwaway test environments) → security groups → NAT gateways → VPC.

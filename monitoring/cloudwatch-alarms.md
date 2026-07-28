# CloudWatch alarms

Create an SNS topic first (e.g. `webapp-ops-alerts`), subscribe the operations team's email or chat webhook to it, then create the following alarms and set each one's alarm action to that topic.

| Alarm | Metric | Condition | Why it matters |
|---|---|---|---|
| High CPU | `AWS/EC2` → `CPUUtilization` (by ASG) | > 70% for 5 minutes | Signals the Auto Scaling group may need to scale out sooner, or that the target-tracking policy isn't keeping up |
| Unhealthy targets | `AWS/ApplicationELB` → `UnHealthyHostCount` | ≥ 1 for 2 consecutive periods (60s) | Instances failing health checks are silently dropped from rotation — worth investigating even before it affects capacity |
| ALB 5xx errors | `AWS/ApplicationELB` → `HTTPCode_Target_5XX_Count` | > 10 in 5 minutes | Application-level errors the ALB itself can't fix |
| Target response time | `AWS/ApplicationELB` → `TargetResponseTime` | > 1 second (average) for 5 minutes | Early warning of performance degradation before users complain |
| RDS CPU | `AWS/RDS` → `CPUUtilization` | > 75% for 10 minutes | Database may be becoming a bottleneck |
| RDS free storage | `AWS/RDS` → `FreeStorageSpace` | < 10% of allocated storage | Prevents running out of disk space unexpectedly |
| RDS connections | `AWS/RDS` → `DatabaseConnections` | Approaching the instance class's max connection limit | Warns before connections start getting refused |

## Composite alarm (optional, reduces noise)

If the team only wants to be paged when CPU is high **and** the ALB is also seeing elevated response times (rather than either alone), combine the "High CPU" and "Target response time" alarms into a CloudWatch composite alarm with an `AND` condition. See the main README's "possible improvements" section.

## Setting this up in the console

1. **SNS** → **Topics** → **Create topic** (Standard) → name it `webapp-ops-alerts` → add an email or chat subscription and confirm it.
2. **CloudWatch** → **Alarms** → **Create alarm** for each row above, selecting the relevant metric and dimension (ASG name, ALB ARN, target group ARN, or DB instance identifier).
3. Set the alarm action to **Send notification to** → `webapp-ops-alerts`.
4. Import `cloudwatch-dashboard.json` under **CloudWatch** → **Dashboards** → **Create dashboard** → **Actions** → **View/edit source**, replacing the `REPLACE_WITH_*` placeholders with your actual resource identifiers.

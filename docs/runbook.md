# Operational runbook

Quick references for responding to the alarms defined in `monitoring/cloudwatch-alarms.md`.

## High CPU alarm fires

1. Check the Auto Scaling group's **Activity history** — it should already be launching new instances if the target-tracking policy triggered correctly.
2. If it hasn't scaled out, check whether the ASG is already at `MaxSize` — raise it temporarily if the traffic increase is expected to continue.
3. If CPU is high but request count is flat, this points to an application-level regression (a slow code path, a runaway loop) rather than a genuine traffic increase — check recent deployments.

## Unhealthy targets alarm fires

1. **EC2** → **Target Groups** → select the target group → **Targets** tab to see which instance(s) are failing and why (check the "Health check details" column).
2. Connect via Session Manager (`aws ssm start-session --target <instance-id>`) and check:
   - `systemctl status webapp` — is the service running?
   - `journalctl -u webapp -n 100` — recent application errors?
   - `curl localhost:8080/health` — does the health check respond locally?
3. If the instance is unrecoverable, terminate it — the Auto Scaling group will replace it automatically.

## ALB 5xx errors alarm fires

1. Check `TargetResponseTime` alongside this alarm — a spike in both usually means the application or database is overloaded, not a code defect.
2. Check CloudWatch Logs for the application (if configured) for stack traces around the alarm's timestamp.
3. If errors correlate with a recent Launch Template update, consider rolling the Auto Scaling group back to the previous Launch Template version.

## RDS failover event

Multi-AZ failover is automatic and typically completes within 60-120 seconds. During failover:

1. The application will see connection errors for a short window — this is expected, not something to "fix" mid-event.
2. Confirm failover completed: **RDS** → **Databases** → check the **Current activity** / event log for a "Multi-AZ instance failover started/completed" entry.
3. After failover, the old primary becomes the new standby in the background — no manual action needed.
4. If failovers are happening more often than expected, check the **RDS recommendations** tab and the CPU/memory alarms — frequent failovers often trace back to resource exhaustion rather than infrastructure issues.

## Auto Scaling group stuck at max capacity for an extended period

1. This is a signal to revisit the `MaxSize` setting and/or the instance type — sustained maximum capacity means the group is capacity-constrained, not just handling a burst.
2. Check whether the load is genuine (marketing event, seasonal traffic) or a symptom of a downstream bottleneck (e.g. the database is slow, so requests pile up and each instance appears "busier" than it should be for the actual traffic volume).

## Connecting to an instance for debugging

```
aws ssm start-session --target <instance-id>
```

No SSH key or bastion host needed — access is controlled by the IAM permissions of whoever runs this command.

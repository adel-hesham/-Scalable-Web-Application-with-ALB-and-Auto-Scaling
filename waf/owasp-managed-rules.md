# AWS WAF rule configuration

Attach these AWS Managed Rule Groups to the Web ACL associated with the ALB.
Managed rules are maintained by AWS and updated automatically as new threats
emerge, which is why this project uses them instead of hand-written rules.

## Managed rule groups to enable

| Rule group | Priority | Purpose |
|---|---|---|
| `AWSManagedRulesCommonRuleSet` | 1 | Broad protection against the OWASP Top 10 (XSS, bad bots, size restrictions) |
| `AWSManagedRulesKnownBadInputsRuleSet` | 2 | Blocks request patterns known to exploit common vulnerabilities |
| `AWSManagedRulesSQLiRuleSet` | 3 | SQL injection protection |
| `AWSManagedRulesAmazonIpReputationList` | 4 | Blocks requests from IPs with poor reputation (botnets, scanners) |
| `AWSManagedRulesLinuxRuleSet` | 5 | Protects against Linux-specific local file inclusion (LFI) attacks |

## Custom rate-based rule

Add a rate-based rule to blunt basic volumetric abuse before it reaches the ALB:

- **Rule type:** Rate-based
- **Rate limit:** 2,000 requests per 5-minute period per source IP
- **Action:** Block
- **Scope:** Applies after the managed rule groups above

## Setting this up in the console

1. Open **WAF & Shield** in the AWS Console → **Web ACLs** → **Create web ACL**.
2. Set **Resource type** to Regional, and **Region** to match your ALB.
3. Under **Add rules**, choose **Add managed rule groups**, and enable each rule group from the table above with the "Count" action first if you want to observe traffic before blocking.
4. Add the custom rate-based rule described above.
5. Set the default action to **Allow**.
6. Under **Associated AWS resources**, select the Application Load Balancer.
7. Review and create.

## Monitoring WAF activity

Enable **CloudWatch metrics** and **sampled requests** on the Web ACL so blocked/counted requests are visible per rule. Consider forwarding WAF logs to an S3 bucket or CloudWatch Logs for longer-term analysis (Kinesis Data Firehose is required for WAF log delivery).

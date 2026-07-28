"""
Scalable Web Application demo.

Serves a small page showing which EC2 instance and Availability Zone handled
the request (via IMDSv2), plus a /health endpoint for the ALB target group.
"""
import requests
from flask import Flask, render_template, jsonify

app = Flask(__name__)

METADATA_TOKEN_URL = "http://169.254.169.254/latest/api/token"
METADATA_BASE_URL = "http://169.254.169.254/latest/meta-data"
METADATA_TIMEOUT_SECONDS = 1


def get_instance_metadata():
    """Fetch instance ID and Availability Zone using IMDSv2 (token-based)."""
    try:
        token = requests.put(
            METADATA_TOKEN_URL,
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=METADATA_TIMEOUT_SECONDS,
        ).text
        headers = {"X-aws-ec2-metadata-token": token}
        instance_id = requests.get(
            f"{METADATA_BASE_URL}/instance-id", headers=headers, timeout=METADATA_TIMEOUT_SECONDS
        ).text
        az = requests.get(
            f"{METADATA_BASE_URL}/placement/availability-zone", headers=headers, timeout=METADATA_TIMEOUT_SECONDS
        ).text
        return instance_id, az
    except requests.exceptions.RequestException:
        # Falls back gracefully when running outside EC2 (e.g. local dev)
        return "local-dev", "unknown"


@app.route("/")
def index():
    instance_id, az = get_instance_metadata()
    return render_template("index.html", instance_id=instance_id, az=az)


@app.route("/health")
def health():
    """Used by the ALB target group health check."""
    return jsonify(status="healthy"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

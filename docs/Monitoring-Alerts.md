# Monitoring & Alerting Strategy

This document outlines the layered approach for surfacing failures and data freshness issues.

## Channels

| Layer | Purpose | Tooling | Destination |
|-------|---------|---------|-------------|
| Runtime Infra | Cloud Run job / Scheduler failures | Cloud Monitoring Alerts | Teams Webhook (+ optional email) |
| Data Pipeline (dbt) | Model/test/freshness failures | GitHub Actions + dbt tests | Teams Webhook |
| Ingestion Quality | Row/metric threshold regressions | Existing Python scripts + CI | Teams (via workflow failure) |
| Historical Trend | Cost & volume anomalies | (Future) BigQuery scheduled queries -> custom metric | Teams / Dashboard |

## Teams Webhook

Secrets:

- `TEAMS_WEBHOOK_URL`: Incoming webhook URL configured in the desired Teams channel.

Scripts:

- `scripts/notify_teams.py` – posts a MessageCard with fallback plain text.

Workflows updated to call this script on failure:

- `.github/workflows/dbt-run-test.yml`
- `.github/workflows/transformations-execute.yml`

## Source Freshness

Defined in `transformations/dbt/models/sources.yml` with 26h warn / 36h error windows. The `dbt source freshness` command in the run/test workflow enforces this.

## Adding Cloud Monitoring Alerts (Outline)

1. Create a notification channel (webhook) pointing to a lightweight relay (see sample below) or directly to Teams if using standard formatting.
2. Policies:

- Cloud Run job execution failures: filter Metric `run.googleapis.com/request_count` with response_code >= 500 (or use error log based alert with `severity=ERROR` and service name filter).
- Cloud Scheduler job failures: Log-based alert on `protoPayload.status.code != 0` and `resource.type="cloud_scheduler_job"`.
- BigQuery job failures: Log-based alert on `resource.type="bigquery_project"` and `protoPayload.serviceData.jobCompletedEvent.job.jobStatus.errorResult:*` with label filter for this project/dataset.
- Data freshness (optional alternative): Scheduled query that checks MAX(timestamp) for raw tables; writes result to a small status table; alert if age > threshold using SQL + Monitoring metric ingestion.

## Example Cloud Function Relay (Python)

Transforms generic alert JSON into a compact Teams message.

```python
import functions_framework, json, os, urllib.request

def _post(webhook, title, text, color="E81123"):
    payload = {"@type":"MessageCard","@context":"http://schema.org/extensions","themeColor":color,"summary":title,"title":title,"text":text}
    req = urllib.request.Request(webhook, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
    urllib.request.urlopen(req, timeout=10)

@functions_framework.http
def alert(request):
    webhook = os.environ['TEAMS_WEBHOOK_URL']
    body = request.get_json(silent=True) or {}
    incident = body.get('incident', {})
    title = incident.get('policy_name', 'GCP Alert')
    state = incident.get('state', 'open')
    summary = incident.get('summary', '')
    url = incident.get('url', '')
    color = 'E81123' if state == 'open' else '107C10'
    text = f"State: {state}\n{summary}\n{url}".strip()
    _post(webhook, title, text, color)
    return ('OK', 200)
```

Deploy (example):

```bash
gcloud functions deploy alert-relay \
  --runtime=python311 --trigger-http --allow-unauthenticated \
  --region=us-central1 --entry-point=alert \
  --set-env-vars=TEAMS_WEBHOOK_URL=YOUR_WEBHOOK
```

Then use the function URL as the Monitoring Webhook channel.

## Failure Message Content Guidelines

Include:

- Repo and workflow (or Cloud Run job) name
- SHA or run ID
- Processing date (for batch jobs)
- Quick next step ("Check run logs" or link to BigQuery job ID)

## Future Enhancements

- Cost anomaly detection (scan bytes vs 7-day moving average > 3σ)
- Adaptive Cards with buttons linking directly to logs
- Multi-env separation (dev vs prod channels)

---
Last updated: YYYY-MM-DD

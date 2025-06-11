# Agent Data System Monitoring Guide

This document provides comprehensive monitoring setup and troubleshooting information for the Agent Data system.

## Overview

The Agent Data system includes monitoring for:
- **Ingestion Workflow Failures**: Alerts when document processing fails
- **Qdrant Performance**: Monitors vector database latency and errors
- **API Performance**: Tracks /vectorize and /auto_tag endpoint health
- **System Health**: Overall system availability and performance

## Alert Policies

### 1. Ingestion Workflow Failure Alert

**File**: `alert_policy_ingestion_workflow.json`

**Monitors**:
- Vectorization step failures (threshold: >2 errors per 5 minutes)
- Auto-tagging step failures (threshold: >2 errors per 5 minutes)
- High overall error rate (threshold: >5 errors per 10 minutes)

**Log Filters**:
```
# Vectorize errors
resource.type="global" AND logName="projects/chatgpt-db-project/logs/ingestion-workflow" AND severity="ERROR" AND jsonPayload.step="vectorize_error"

# Auto-tag errors
resource.type="global" AND logName="projects/chatgpt-db-project/logs/ingestion-workflow" AND severity="ERROR" AND jsonPayload.step="auto_tag_error"

# General workflow errors
resource.type="global" AND logName="projects/chatgpt-db-project/logs/ingestion-workflow" AND severity="ERROR"
```

### 2. Qdrant Performance Alert

**File**: `alert_policy_qdrant_latency.json`

**Monitors**:
- High query latency (threshold: >2 seconds)
- Connection failures
- Vector upsert errors

## Deployment

### Prerequisites

1. **Google Cloud CLI**: Install and authenticate
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash

   # Authenticate
   gcloud auth login
   gcloud config set project chatgpt-db-project
   ```

2. **Required Permissions**:
   - `monitoring.alertPolicies.create`
   - `monitoring.alertPolicies.update`
   - `monitoring.alertPolicies.list`

### Deploy Alert Policies

```bash
# Deploy all monitoring alerts
./scripts/deploy_monitoring_alerts.sh
```

**Manual Deployment**:
```bash
# Deploy ingestion workflow alerts
gcloud alpha monitoring policies create \
    --policy-from-file=alert_policy_ingestion_workflow.json

# Deploy Qdrant performance alerts
gcloud alpha monitoring policies create \
    --policy-from-file=alert_policy_qdrant_latency.json
```

### Verify Deployment

```bash
# List all alert policies
gcloud alpha monitoring policies list \
    --filter="displayName:('Ingestion Workflow' OR 'Qdrant')" \
    --format="table(displayName,enabled,conditions.len():label=CONDITIONS)"
```

## Notification Channels

### Setup Email Notifications

```bash
# Create email notification channel
gcloud alpha monitoring channels create \
    --display-name="Agent Data Alerts" \
    --type=email \
    --channel-labels=email_address=your-email@domain.com
```

### Setup Slack Notifications

1. Create Slack webhook URL in your Slack workspace
2. Create notification channel:
   ```bash
   gcloud alpha monitoring channels create \
       --display-name="Agent Data Slack" \
       --type=slack \
       --channel-labels=url=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
   ```

### Link Notification Channels to Alert Policies

```bash
# Get notification channel ID
CHANNEL_ID=$(gcloud alpha monitoring channels list \
    --filter="displayName:'Agent Data Alerts'" \
    --format="value(name)")

# Update alert policy with notification channel
gcloud alpha monitoring policies update POLICY_NAME \
    --add-notification-channels=$CHANNEL_ID
```

## Monitoring Dashboards

### Cloud Monitoring Console

Access the monitoring console at:
https://console.cloud.google.com/monitoring/alerting/policies?project=chatgpt-db-project

### Key Metrics to Monitor

1. **Ingestion Workflow**:
   - Success rate: `>95%`
   - Processing time: `<5 minutes per document`
   - Error rate: `<5%`

2. **API Endpoints**:
   - `/vectorize` response time: `<30 seconds`
   - `/auto_tag` response time: `<10 seconds`
   - Error rate: `<1%`

3. **Qdrant Performance**:
   - Query latency: `<2 seconds`
   - Upsert latency: `<5 seconds`
   - Connection success rate: `>99%`

## Troubleshooting

### Common Alert Scenarios

#### 1. Ingestion Workflow Vectorize Failures

**Symptoms**: High error rate in vectorization step

**Possible Causes**:
- OpenAI API rate limits or quota exceeded
- Invalid document format or content
- Network connectivity issues
- Qdrant connection problems

**Investigation Steps**:
```bash
# Check recent workflow logs
gcloud logging read "logName='projects/chatgpt-db-project/logs/ingestion-workflow' AND severity='ERROR' AND jsonPayload.step='vectorize_error'" \
    --limit=10 \
    --format=json

# Check OpenAI API usage
# (Check OpenAI dashboard for rate limits and quota)

# Test Qdrant connectivity
curl -H "api-key: $QDRANT_API_KEY" \
    "$QDRANT_URL/collections"
```

#### 2. Auto-Tagging Failures

**Symptoms**: High error rate in auto-tagging step

**Possible Causes**:
- OpenAI API issues
- Invalid content for tagging
- Function timeout

**Investigation Steps**:
```bash
# Check auto-tag specific logs
gcloud logging read "logName='projects/chatgpt-db-project/logs/ingestion-workflow' AND severity='ERROR' AND jsonPayload.step='auto_tag_error'" \
    --limit=10 \
    --format=json

# Check function execution time
gcloud logging read "resource.type='cloud_function' AND resource.labels.function_name='auto-tag-function'" \
    --limit=10
```

#### 3. High Qdrant Latency

**Symptoms**: Slow vector operations

**Possible Causes**:
- High query load
- Network latency
- Qdrant cluster performance issues
- Large vector collections

**Investigation Steps**:
```bash
# Check Qdrant cluster status
curl -H "api-key: $QDRANT_API_KEY" \
    "$QDRANT_URL/cluster"

# Check collection sizes
curl -H "api-key: $QDRANT_API_KEY" \
    "$QDRANT_URL/collections" | jq '.result.collections[] | {name: .name, vectors_count: .vectors_count}'

# Monitor query patterns
gcloud logging read "resource.type='gce_instance' AND jsonPayload.component='qdrant'" \
    --limit=20
```

### Performance Optimization

#### 1. Reduce Ingestion Workflow Latency

- **Batch Processing**: Process multiple documents in parallel
- **Caching**: Cache frequently used embeddings
- **Retry Logic**: Implement exponential backoff for transient failures

#### 2. Optimize Qdrant Performance

- **Index Configuration**: Tune HNSW parameters for your use case
- **Collection Sharding**: Distribute large collections across shards
- **Query Optimization**: Use appropriate filters and limits

#### 3. API Rate Limiting

- **OpenAI**: Implement rate limiting and retry logic
- **Qdrant**: Use connection pooling and batch operations
- **Firestore**: Optimize read/write patterns

## Testing Alerts

### Simulate Workflow Failures

```bash
# Test vectorize failure alert
gcloud logging write ingestion-workflow \
    '{"severity": "ERROR", "jsonPayload": {"step": "vectorize_error", "error": "Test alert", "doc_id": "test-123"}}' \
    --severity=ERROR

# Test auto-tag failure alert
gcloud logging write ingestion-workflow \
    '{"severity": "ERROR", "jsonPayload": {"step": "auto_tag_error", "error": "Test alert", "doc_id": "test-456"}}' \
    --severity=ERROR
```

### Validate Alert Delivery

1. Check alert policy status in Cloud Monitoring console
2. Verify notification channels receive test alerts
3. Monitor alert resolution time

## Maintenance

### Regular Tasks

1. **Weekly**: Review alert policy performance and adjust thresholds
2. **Monthly**: Analyze error patterns and optimize system performance
3. **Quarterly**: Update notification channels and escalation procedures

### Alert Policy Updates

```bash
# Update existing alert policy
gcloud alpha monitoring policies update POLICY_NAME \
    --policy-from-file=updated_policy.json

# List policy history
gcloud alpha monitoring policies list \
    --format="table(displayName,creationRecord.mutatedBy,creationRecord.mutateTime)"
```

## Support

### Escalation Procedures

1. **Level 1**: Automated alerts → On-call engineer
2. **Level 2**: Persistent issues → Development team
3. **Level 3**: System-wide outage → Engineering manager

### Contact Information

- **Development Team**: agent-data-dev@company.com
- **On-Call**: +1-XXX-XXX-XXXX
- **Slack Channel**: #agent-data-alerts

### External Dependencies

- **OpenAI API Status**: https://status.openai.com/
- **Qdrant Cloud Status**: https://status.qdrant.io/
- **Google Cloud Status**: https://status.cloud.google.com/

---

*Last Updated: January 2025*
*Version: 1.0*

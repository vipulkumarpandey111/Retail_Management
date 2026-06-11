$groupId = if ($args.Count -ge 1) { $args[0] } else { "retailflow-demo-group-a" }
$consumerName = if ($args.Count -ge 2) { $args[1] } else { "consumer-1" }
$topics = if ($args.Count -ge 3) { $args[2] } else { "retailflow.direct.order_signals.partitioned" }

$env:KAFKA_GROUP_ID = $groupId
$env:KAFKA_CONSUMER_NAME = $consumerName
$env:KAFKA_CONSUMER_TOPICS = $topics

Write-Host "Starting Kafka consumer"
Write-Host "  group id      : $groupId"
Write-Host "  consumer name : $consumerName"
Write-Host "  topics        : $topics"

.\.venv\Scripts\python workers\kafka_consumer\main.py

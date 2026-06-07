$topicName = if ($args.Count -ge 1) { $args[0] } else { "retailflow.direct.order_signals.partitioned" }

docker exec retailflow-kafka kafka-topics `
  --bootstrap-server kafka:29092 `
  --describe `
  --topic $topicName

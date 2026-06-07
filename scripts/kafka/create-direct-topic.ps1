$topicName = if ($args.Count -ge 1) { $args[0] } else { "retailflow.direct.order_signals.partitioned" }
$partitions = if ($args.Count -ge 2) { $args[1] } else { "3" }
$replicationFactor = if ($args.Count -ge 3) { $args[2] } else { "1" }

docker exec retailflow-kafka kafka-topics `
  --bootstrap-server kafka:29092 `
  --create `
  --if-not-exists `
  --topic $topicName `
  --partitions $partitions `
  --replication-factor $replicationFactor

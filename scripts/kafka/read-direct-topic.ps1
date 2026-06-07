$topicName = if ($args.Count -ge 1) { $args[0] } else { "retailflow.direct.order_signals" }

docker exec -it retailflow-kafka kafka-console-consumer `
  --bootstrap-server kafka:29092 `
  --topic $topicName `
  --from-beginning `
  --property print.key=true `
  --property print.partition=true `
  --property print.offset=true `
  --property key.separator=" | "


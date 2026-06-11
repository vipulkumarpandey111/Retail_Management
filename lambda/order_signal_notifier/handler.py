import json
import os

import boto3


def get_sns_client():
    return boto3.client("sns", region_name=os.getenv("AWS_REGION", "ap-south-1"))


def handler(event, _context):
    topic_arn = os.getenv("AWS_SNS_TOPIC_ARN", "")
    results = []

    for record in event.get("Records", []):
        body = record.get("body", "{}")
        payload = json.loads(body)
        summary = {
            "event_type": payload.get("event_type"),
            "source": payload.get("source"),
            "payload_keys": sorted(payload.get("payload", {}).keys()),
        }

        publish_result = None
        if topic_arn:
            response = get_sns_client().publish(
                TopicArn=topic_arn,
                Subject=(payload.get("event_type") or "retailflow-event")[:100],
                Message=json.dumps(
                    {
                        "summary": summary,
                        "original_message": payload,
                        "lambda_source": "order-signal-notifier",
                    },
                    default=str,
                ),
            )
            publish_result = {"message_id": response.get("MessageId")}

        results.append(
            {
                "message_id": record.get("messageId"),
                "summary": summary,
                "sns_publish_result": publish_result,
            }
        )

    return {
        "processed_records": len(results),
        "results": results,
    }

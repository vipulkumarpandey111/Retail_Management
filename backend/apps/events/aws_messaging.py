import json

import boto3
from django.conf import settings


def get_sqs_client():
    return boto3.client("sqs", region_name=settings.AWS_REGION)


def get_sns_client():
    return boto3.client("sns", region_name=settings.AWS_REGION)


def publish_sqs_message(event_type, payload, queue_url=None, message_group_id=None):
    target_queue_url = queue_url or settings.AWS_SQS_QUEUE_URL
    if not target_queue_url:
        raise ValueError("AWS_SQS_QUEUE_URL is not configured")

    message = {
        "event_type": event_type,
        "payload": payload,
        "source": "django-api-sqs-publisher",
    }

    request = {
        "QueueUrl": target_queue_url,
        "MessageBody": json.dumps(message, default=str),
        "MessageAttributes": {
            "event_type": {
                "DataType": "String",
                "StringValue": event_type,
            }
        },
    }

    if message_group_id:
        request["MessageGroupId"] = message_group_id

    response = get_sqs_client().send_message(**request)
    return {
        "queue_url": target_queue_url,
        "message_id": response.get("MessageId"),
        "md5_of_body": response.get("MD5OfMessageBody"),
        "message_group_id": message_group_id,
        "message": message,
    }


def publish_sns_message(event_type, payload, topic_arn=None, subject=None):
    target_topic_arn = topic_arn or settings.AWS_SNS_TOPIC_ARN
    if not target_topic_arn:
        raise ValueError("AWS_SNS_TOPIC_ARN is not configured")

    message = {
        "event_type": event_type,
        "payload": payload,
        "source": "django-api-sns-publisher",
    }

    response = get_sns_client().publish(
        TopicArn=target_topic_arn,
        Subject=subject or event_type[:100],
        Message=json.dumps(message, default=str),
        MessageAttributes={
            "event_type": {
                "DataType": "String",
                "StringValue": event_type,
            }
        },
    )
    return {
        "topic_arn": target_topic_arn,
        "message_id": response.get("MessageId"),
        "subject": subject or event_type[:100],
        "message": message,
    }

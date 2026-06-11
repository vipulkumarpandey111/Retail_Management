import json
import os

import boto3
from botocore.config import Config
from django.conf import settings


def get_aws_env_diagnostics():
    return {
        "aws_access_key_id_configured": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "aws_secret_access_key_configured": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
        "aws_session_token_configured": bool(os.getenv("AWS_SESSION_TOKEN")),
        "aws_default_region_configured": bool(
            os.getenv("AWS_DEFAULT_REGION") or os.getenv("AWS_REGION")
        ),
        "aws_ec2_metadata_disabled": os.getenv("AWS_EC2_METADATA_DISABLED", ""),
        "http_proxy_configured": bool(os.getenv("HTTP_PROXY") or os.getenv("http_proxy")),
        "https_proxy_configured": bool(os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")),
    }


def _build_boto3_config():
    # Local dev environments sometimes inherit a broken proxy setting.
    # These sample AWS clients should talk directly to AWS unless the user
    # explicitly chooses a valid proxy path later.
    return Config(proxies={})


def _prepare_local_aws_sdk_behavior():
    # This project runs outside EC2 for local learning, so disabling IMDS
    # avoids noisy fallback attempts when credentials should come from env vars
    # or the shared AWS config/credentials files.
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")


def _build_explicit_credentials_kwargs():
    access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    session_token = os.getenv("AWS_SESSION_TOKEN", "")

    if access_key_id and secret_access_key:
        kwargs = {
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": secret_access_key,
        }
        if session_token:
            kwargs["aws_session_token"] = session_token
        return kwargs

    raise RuntimeError(
        "AWS credentials are not visible to the Django process. "
        "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in the same terminal "
        "before starting runserver."
    )


def get_sqs_client():
    _prepare_local_aws_sdk_behavior()
    return boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
        config=_build_boto3_config(),
        **_build_explicit_credentials_kwargs(),
    )


def get_sns_client():
    _prepare_local_aws_sdk_behavior()
    return boto3.client(
        "sns",
        region_name=settings.AWS_REGION,
        config=_build_boto3_config(),
        **_build_explicit_credentials_kwargs(),
    )


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

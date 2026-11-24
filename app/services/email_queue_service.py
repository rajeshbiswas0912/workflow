import json

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config.settings import settings

_sqs = boto3.client("sqs", region_name=settings.AWS_REGION_NAME)


def enqueue_welcome_email(*, employee_id: int, email: str, name: str, temporary_password: str) -> None:
    if not settings.EMAIL_QUEUE_URL:
        return
    try:
        _sqs.send_message(
            QueueUrl=settings.EMAIL_QUEUE_URL,
            MessageBody=json.dumps(
                {
                    "type": "welcome_email",
                    "employee_id": employee_id,
                    "email": email,
                    "name": name,
                    "temporary_password": temporary_password,
                }
            ),
        )
    except (BotoCoreError, ClientError):
        pass

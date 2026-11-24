import json
import os

import boto3
import traceback

from app.emails import render_email

ses = boto3.client("sesv2", region_name=os.environ.get("AWS_REGION_NAME"))

EMAIL_FROM = os.environ["EMAIL_FROM"]

def _send(message: dict) -> None:
    content = render_email(message["type"], message)
    ses.send_email(
        FromEmailAddress=EMAIL_FROM,
        Destination={"ToAddresses": [message["email"]]},
        Content={
            "Simple": {
                "Subject": {"Data": content.subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": content.text, "Charset": "UTF-8"},
                    "Html": {"Data": content.html, "Charset": "UTF-8"},
                },
            }
        },
    )


def handler(event, context):
    failures = []
    for record in event["Records"]:
        try:
            _send(json.loads(record["body"]))
        except Exception:
            traceback.print_exc()
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}

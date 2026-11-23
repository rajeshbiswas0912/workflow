import json
import os


def load_aws_secrets() -> None:
    """When running on AWS Lambda, copy secrets from Secrets Manager into
    environment variables so Settings() picks them up. Does nothing locally."""
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return

    import boto3

    client = boto3.client("secretsmanager")

    # Database login (created automatically by RDS)
    db = json.loads(
        client.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"]
    )
    os.environ["DB_USER"] = db["username"]
    os.environ["DB_PASSWORD"] = db["password"]

    # Your app secrets: every key in this secret becomes an environment variable
    # (for you: SECRET_KEY and ADMIN_PASSWORD)
    app = json.loads(
        client.get_secret_value(SecretId=os.environ["APP_SECRET_ARN"])["SecretString"]
    )
    for key, value in app.items():
        os.environ[key] = str(value)

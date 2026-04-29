import base64
import json
import os
import time
import uuid
from datetime import datetime, timezone

import boto3

firehose = boto3.client("firehose")
sqs = boto3.client("sqs")

STREAM_NAME = os.environ["FIREHOSE_STREAM_NAME"]
FAILED_EVENTS_QUEUE_URL = os.environ["FAILED_EVENTS_QUEUE_URL"]
EVENT_API_KEY = os.environ["EVENT_API_KEY"]


def log(level, message, **kwargs):
    print(json.dumps({
        "level": level,
        "message": message,
        **kwargs
    }))


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(body),
    }


def parse_body(event):
    raw_body = event.get("body") or "{}"

    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(raw_body).decode("utf-8")

    return json.loads(raw_body)


def validate_schema(payload):
    required_fields = ["event_type", "user_id", "timestamp", "properties"]

    missing_fields = [
        field for field in required_fields if field not in payload
    ]

    if missing_fields:
        return False, f"Missing required fields: {missing_fields}"

    if not isinstance(payload["event_type"], str) or not payload["event_type"].strip():
        return False, "event_type must be a non-empty string"

    if not isinstance(payload["user_id"], str) or not payload["user_id"].strip():
        return False, "user_id must be a non-empty string"

    if not isinstance(payload["properties"], dict):
        return False, "properties must be an object"

    try:
        datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        return False, "timestamp must be a valid ISO-8601 datetime"

    if "source" in payload and payload["source"] not in ["web", "mobile", "unknown"]:
        return False, "source must be one of: web, mobile, unknown"

    return True, None


def send_to_dlq(payload, reason):
    message = {
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "payload": payload,
    }

    sqs.send_message(
        QueueUrl=FAILED_EVENTS_QUEUE_URL,
        MessageBody=json.dumps(message),
    )


def handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")

    try:
        if event.get("httpMethod") == "OPTIONS":
            return response(200, {"message": "ok"})

        headers = event.get("headers") or {}
        provided_api_key = headers.get("x-api-key") or headers.get("X-Api-Key")

        if provided_api_key != EVENT_API_KEY:
            log("WARN", "Unauthorized request", request_id=request_id)
            return response(401, {"message": "Unauthorized"})

        payload = parse_body(event)

        is_valid, validation_error = validate_schema(payload)

        if not is_valid:
            log(
                "WARN",
                "Invalid event payload",
                request_id=request_id,
                validation_error=validation_error,
            )

            return response(
                400,
                {
                    "message": "Invalid event payload",
                    "error": validation_error,
                },
            )

        enriched_event = {
            "event_id": str(uuid.uuid4()),
            "received_at": int(time.time()),
            "event_type": payload["event_type"],
            "user_id": payload["user_id"],
            "timestamp": payload["timestamp"],
            "properties": payload["properties"],
            "source": payload.get("source", "unknown"),
            "schema_version": payload.get("schema_version", "1.0"),
        }

        log(
            "INFO",
            "Event accepted",
            request_id=request_id,
            event_id=enriched_event["event_id"],
            event_type=enriched_event["event_type"],
            source=enriched_event["source"],
        )

        try:
            force_firehose_error = headers.get("x-force-firehose-error") or headers.get("X-Force-Firehose-Error")
            if force_firehose_error == "true":
                raise Exception("Forced Firehose error for DLQ testing")
            firehose.put_record(
                DeliveryStreamName=STREAM_NAME,
                Record={
                    "Data": json.dumps(enriched_event) + "\n"
                },
            )
        except Exception as firehose_error:
            log(
                "ERROR",
                "Failed to write event to Firehose",
                request_id=request_id,
                error=str(firehose_error),
            )

            send_to_dlq(enriched_event, str(firehose_error))

            return response(
                202,
                {
                    "message": "Event accepted but routed to DLQ",
                    "event_id": enriched_event["event_id"],
                },
            )

        return response(
            202,
            {
                "message": "Event accepted",
                "event_id": enriched_event["event_id"],
            },
        )

    except json.JSONDecodeError:
        log("WARN", "Invalid JSON body", request_id=request_id)
        return response(400, {"message": "Invalid JSON body"})

    except Exception as error:
        log("ERROR", "Unexpected error", request_id=request_id, error=str(error))
        return response(500, {"message": "Internal server error"})
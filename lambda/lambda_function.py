import json
import os
import random
import string
import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))

def respond(status, body=None, headers=None):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **(headers or {})},
        "body": json.dumps(body) if body is not None else "",
    }

def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method == "POST":
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return respond(400, {"error": "Invalid JSON"})
        url = body.get("url", "")
        if not url.startswith(("http://", "https://")):
            return respond(400, {"error": "url must start with http:// or https://"})
        code = generate_code()
        table.put_item(Item={"short_code": code, "long_url": url})
        return respond(200, {"short_code": code})

    if method == "GET":
        code = (event.get("pathParameters") or {}).get("code")
        item = table.get_item(Key={"short_code": code}).get("Item")
        if not item:
            return respond(404, {"error": "Short link not found"})
        return respond(301, headers={"Location": item["long_url"]})

    return respond(400, {"error": "Unsupported request"})
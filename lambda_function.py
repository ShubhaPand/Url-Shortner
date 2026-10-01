import json, os, random, string, time
import boto3
from botocore.exceptions import ClientError

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
BASE_URL = os.environ.get("BASE_URL", "")

def make_code(n=6):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(n))

def resp(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }

def lambda_handler(event, context):
    route = event["routeKey"]
    if route == "POST /shorten":
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return resp(400, {"error": "Invalid JSON"})
        url = (body.get("url") or "").strip()
        if not url.startswith(("http://", "https://")) or len(url) > 2000:
            return resp(400, {"error": "Please provide a valid http(s) URL"})
        for _ in range(5):
            code = make_code()
            try:
                table.put_item(
                    Item={"code": code, "long_url": url, "created_at": int(time.time())},
                    ConditionExpression="attribute_not_exists(code)",
                )
                return resp(200, {"short_url": f"{BASE_URL}/{code}"})
            except ClientError as e:
                if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
        return resp(500, {"error": "Could not generate a code, try again"})
    if route == "GET /{code}":
        code = ((event.get("pathParameters") or {}).get("code") or "").strip()
        if not code:
            return resp(400, {"error": "No short code provided"})
        item = table.get_item(Key={"code": code}).get("Item")
        if not item:
            return resp(404, {"error": "Link not found"})
        return {"statusCode": 302, "headers": {"Location": item["long_url"]}}

    return resp(404, {"error": "Not found"})

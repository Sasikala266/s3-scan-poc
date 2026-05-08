import json
import os
import logging
from typing import Dict, List, Optional, Any

import boto3
from botocore.exceptions import ClientError
from config import FILE_TYPE_PREFIXES

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AWS_REGION = os.environ.get("REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

s3_client = boto3.client("s3", region_name=AWS_REGION)

ALLOWED_EXTENSIONS = {"csv", "json", "xml", "html"}

def response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "content-type",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps(body)
    }

def extract_filename_only(value: str) -> str:
    if not value:
        return value
    v = value.strip().strip('"').strip("'")
    if v.startswith("s3://"):
        parts = v.replace("s3://", "", 1).split("/", 1)
        v = parts[1] if len(parts) > 1 else ""
    if "/" in v:
        v = v.split("/")[-1]
    return v.strip()

def extract_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

def determine_search_prefixes(file_ext: str) -> List[str]:
    prefixes = FILE_TYPE_PREFIXES.get(file_ext)
    if not prefixes:
        prefixes = FILE_TYPE_PREFIXES.get("default", [])
    return prefixes

def find_file_in_prefix(bucket_name: str, search_prefix: str, target_filename: str) -> Optional[str]:
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=search_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.split("/")[-1] == target_filename:
                    return key
        return None
    except ClientError as e:
        logger.error(f"S3 error while searching prefix '{search_prefix}': {e}")
        return None

def locate_file_in_bucket(bucket_name: str, target_filename: str) -> Optional[str]:
    file_ext = extract_file_extension(target_filename)
    prefixes = determine_search_prefixes(file_ext)
    for prefix in prefixes:
        found_key = find_file_in_prefix(bucket_name, prefix, target_filename)
        if found_key:
            return f"s3://{bucket_name}/{found_key}"
    return None

def parse_input(event: Dict[str, Any]) -> Dict[str, Any]:
    # Query string fallback (REST API)
    qsp = event.get("queryStringParameters") or {}
    if isinstance(qsp, dict) and (qsp.get("file_name") or qsp.get("filename")):
        return qsp

    # Direct test event
    if event.get("file_name") or event.get("filename"):
        return event

    # API Gateway proxy body
    body = event.get("body")
    if not body:
        return {}

    if event.get("isBase64Encoded") is True:
        import base64
        body = base64.b64decode(body).decode("utf-8", errors="replace")

    if isinstance(body, str):
        s = body.strip()
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {"file_name": str(parsed)}
        except Exception:
            # body is plain string => treat as filename
            return {"file_name": s}

    if isinstance(body, dict):
        return body

    return {}

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    if not S3_BUCKET:
        return response(500, {
            "status": "error",
            "message": "S3_BUCKET_NAME environment variable is not configured."
        })

    payload = parse_input(event)
    file_name = payload.get("file_name") or payload.get("filename")
    file_name = extract_filename_only(file_name) if file_name else file_name

    if not file_name:
        return response(400, {
            "status": "error",
            "message": "Please provide a file name to search (example: employee_data.csv)."
        })

    ext = extract_file_extension(file_name)
    if not ext:
        return response(400, {
            "status": "error",
            "message": "Invalid file name. Please include an extension (example: employee_data.csv / sample.json / data.xml / page.html)."
        })

    if ext not in ALLOWED_EXTENSIONS:
        return response(400, {
            "status": "error",
            "message": f"Unsupported file type '.{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        })

    s3_uri = locate_file_in_bucket(S3_BUCKET, file_name)
    if s3_uri:
        return response(200, {
            "status": "success",
            "file_name": file_name,
            "s3_uri": s3_uri,
            "message": "File found successfully."
        })

    return response(404, {
        "status": "not_found",
        "file_name": file_name,
        "message": f"File not found. Searched in: {', '.join(determine_search_prefixes(ext))}"
    })

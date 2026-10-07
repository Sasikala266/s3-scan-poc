import json
import os
import logging
import fnmatch
from typing import Dict, List, Optional, Any

import boto3
from botocore.exceptions import ClientError
from config import FILE_TYPE_PREFIXES

# -------------------------
# Logging
# -------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -------------------------
# Environment Variables
# -------------------------
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

# -------------------------
# AWS Clients
# -------------------------
s3_client = boto3.client("s3", region_name=AWS_REGION)

# -------------------------
# Validation Config
# -------------------------
ALLOWED_EXTENSIONS = {"csv", "json", "xml", "html"}

# -------------------------
# Helper Functions
# -------------------------
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
    value = value.strip().strip('"').strip("'")
    if value.startswith("s3://"):
        parts = value.replace("s3://", "", 1).split("/", 1)
        value = parts[1] if len(parts) > 1 else ""
    if "/" in value:
        value = value.split("/")[-1]
    return value.strip()


def extract_file_extension(filename: str) -> str:
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return ""


def determine_search_prefixes(file_ext: str) -> List[str]:
    prefixes = FILE_TYPE_PREFIXES.get(file_ext)
    if not prefixes:
        prefixes = FILE_TYPE_PREFIXES.get("default", [])
    return prefixes


def is_wildcard_pattern(file_name: str) -> bool:
    return "*" in file_name or "?" in file_name


def parse_input(event: Dict[str, Any]) -> Dict[str, Any]:
    # Query string support
    qsp = event.get("queryStringParameters") or {}
    if isinstance(qsp, dict) and (qsp.get("file_name") or qsp.get("filename")):
        return qsp

    # Direct Lambda test event
    if event.get("file_name") or event.get("filename"):
        return event

    # API Gateway
    body = event.get("body")
    if not body:
        return {}

    if event.get("isBase64Encoded") is True:
        import base64
        body = base64.b64decode(body).decode("utf-8", errors="replace")

    if isinstance(body, str):
        body = body.strip()
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                return parsed
            return {"file_name": str(parsed)}
        except Exception:
            return {"file_name": body}

    if isinstance(body, dict):
        return body

    return {}


def find_exact_file_in_prefix(bucket_name: str, search_prefix: str, target_filename: str) -> Optional[str]:
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=search_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.split("/")[-1] == target_filename:
                    logger.info(f"Exact match found: {key}")
                    return key
        return None
    except ClientError as error:
        logger.error(f"S3 error in prefix {search_prefix}: {str(error)}")
        return None


def locate_exact_file_in_bucket(bucket_name: str, target_filename: str) -> Optional[str]:
    file_ext = extract_file_extension(target_filename)
    search_prefixes = determine_search_prefixes(file_ext)

    logger.info(f"Searching exact file '{target_filename}' in prefixes: {search_prefixes}")

    for prefix in search_prefixes:
        found_key = find_exact_file_in_prefix(bucket_name, prefix, target_filename)
        if found_key:
            return found_key

    return None


def find_wildcard_matches_in_prefix(bucket_name: str, search_prefix: str, pattern: str) -> List[str]:
    matches = []
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=search_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                file_name = key.split("/")[-1]

                # case-insensitive matching
                if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                    matches.append(key)

        logger.info(f"Wildcard matches under prefix '{search_prefix}': {len(matches)}")
        return matches

    except ClientError as error:
        logger.error(f"S3 error in wildcard prefix {search_prefix}: {str(error)}")
        return []


def locate_wildcard_matches_in_bucket(bucket_name: str, pattern: str) -> List[str]:
    file_ext = extract_file_extension(pattern)
    search_prefixes = determine_search_prefixes(file_ext)

    logger.info(f"Searching wildcard pattern '{pattern}' in prefixes: {search_prefixes}")

    all_matches = []
    for prefix in search_prefixes:
        all_matches.extend(find_wildcard_matches_in_prefix(bucket_name, prefix, pattern))

    # de-duplicate while keeping order
    deduped = list(dict.fromkeys(all_matches))
    return deduped


# -------------------------
# Lambda Handler
# -------------------------
def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
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
                "message": "Please provide a file name or wildcard pattern to search (example: employee_data.csv or sam*.json)."
            })

        file_ext = extract_file_extension(file_name)
        if not file_ext:
            return response(400, {
                "status": "error",
                "message": "Invalid file name or pattern. Please include a valid extension (example: employee_data.csv or sam*.json)."
            })

        if file_ext not in ALLOWED_EXTENSIONS:
            return response(400, {
                "status": "error",
                "message": f"Unsupported file type '.{file_ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            })

        # -------------------------
        # Wildcard search
        # -------------------------
        if is_wildcard_pattern(file_name):
            matched_keys = locate_wildcard_matches_in_bucket(S3_BUCKET, file_name)

            if matched_keys:
                return response(200, {
                    "status": "success",
                    "search_type": "wildcard",
                    "pattern": file_name,
                    "match_count": len(matched_keys),
                    "relative_paths": matched_keys,
                    "s3_uris": [f"s3://{S3_BUCKET}/{key}" for key in matched_keys],
                    "message": "Matching files found successfully."
                })

            return response(404, {
                "status": "not_found",
                "search_type": "wildcard",
                "pattern": file_name,
                "message": "No matching files found."
            })

        # -------------------------
        # Exact search
        # -------------------------
        matched_key = locate_exact_file_in_bucket(S3_BUCKET, file_name)

        if matched_key:
            return response(200, {
                "status": "success",
                "search_type": "exact",
                "file_name": file_name,
                "relative_path": matched_key,
                "s3_uri": f"s3://{S3_BUCKET}/{matched_key}",
                "message": "File found successfully."
            })

        return response(404, {
            "status": "not_found",
            "search_type": "exact",
            "file_name": file_name,
            "message": "File not found in S3 under expected paths."
        })

    except Exception as e:
        logger.error("Unexpected error", exc_info=True)
        return response(500, {
            "status": "error",
            "message": f"Unexpected error occurred: {str(e)}"
        })

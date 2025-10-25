from datetime import datetime, timedelta, timezone
import logging
from time import time
from typing import Dict, Any
from urllib.parse import urlparse

from boto3.session import Session as AWSSession
from botocore.config import Config
from botocore.exceptions import ClientError
from freezegun import freeze_time
from mypy_boto3_s3.client import S3Client
from redis.asyncio import Redis
import structlog

from app.core.config import settings

logger = structlog.stdlib.get_logger("ext.s3")


def get_resource_prefix() -> str:
    now = datetime.now(timezone.utc)
    return datetime.strftime(now, "%Y/%m/%d")


def parse_s3_uri(uri: str) -> Dict[str, str]:
    o = urlparse(uri)
    return {"Bucket": o.netloc, "Key": o.path.lstrip("/")}


def get_s3_client(session: AWSSession) -> S3Client:
    return session.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        config=Config(
            region_name=settings.AWS_DEFAULT_REGION,
            s3={"addressing_style": "virtual"},
        ),
    )


def create_presigned_post(session: AWSSession, object_name: str) -> Dict[str, Any]:
    expiry = timedelta(hours=1)
    logger.info(
        "Creating presigned POST",
        object_name=object_name,
        expiry=(datetime.now(timezone.utc) + expiry).isoformat(),
    )

    s3_client = get_s3_client(session)
    bucket_key = f"{get_resource_prefix()}/{object_name}"
    try:
        response = s3_client.generate_presigned_post(
            settings.IMAGES_BUCKET,
            bucket_key,
            Conditions=[
                ["content-length-range", 1, 10 * 1000 * 1000],
                {"bucket": (settings.IMAGES_BUCKET)},
            ],
            ExpiresIn=int(expiry.total_seconds()),
        )
    except ClientError:
        logger.exception("Failed to create presigned POST")
        return None

    # The response contains the presigned URL and required fields
    return {
        "create_response": response,
        "s3_uri": f"s3://{settings.IMAGES_BUCKET}/{bucket_key}",
    }


def create_presigned_url(session: AWSSession, s3_uri: str, content_type: str) -> str:
    s3_client = get_s3_client(session)

    try:
        current_timestamp = time()
        cache_age = settings.PRESIGNED_URL_EXPIRY - int(
            timedelta(hours=1).total_seconds()
        )
        frozen_timestamp = datetime.fromtimestamp(
            current_timestamp - (current_timestamp % settings.PRESIGNED_URL_EXPIRY)
        )

        logger.info(
            "Creating presigned URL",
            s3_uri=s3_uri,
            content_type=content_type,
            cache_age=cache_age,
            expiry=settings.PRESIGNED_URL_EXPIRY,
            frozen_timestamp=frozen_timestamp.isoformat(),
        )

        # Freeze the time at the beginning of the epoch week to allow browser to
        # cache the presigned URL for a week
        with freeze_time(frozen_timestamp):
            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params=parse_s3_uri(s3_uri)
                | {
                    "ResponseContentType": content_type,
                    "ResponseCacheControl": f"private, max-age={cache_age}, immutable",
                },
                ExpiresIn=settings.PRESIGNED_URL_EXPIRY,
            )

            # Replace the S3 hostname with the Cloudfront distribution in production
            if settings.PRODUCTION:
                return (
                    urlparse(presigned_url)
                    ._replace(netloc=(settings.IMAGES_CLOUDFRONT_DISTRIBUTION))
                    .geturl()
                )

            return presigned_url
    except ClientError:
        logger.exception("Failed to create presigned URL")
        return None


async def presigned_url_with_cache(
    session: AWSSession, redis: Redis, s3_uri: str, content_type: str
) -> str:
    await logger.ainfo(
        "Attempting to lookup presigned URL for S3 object in Redis", s3_uri=s3_uri
    )
    redis_key = f"s3_presigned_url:{s3_uri}"
    cached_url: str = await redis.get(redis_key)
    if cached_url:
        await logger.ainfo("Found presigned URL for S3 object in Redis", s3_uri=s3_uri)
        return cached_url

    await logger.ainfo(
        "Presigned URL not found in Redis, creating new presigned URL", s3_uri=s3_uri
    )
    presigned_url = create_presigned_url(session, s3_uri, content_type)
    if presigned_url:
        await redis.set(redis_key, presigned_url, ex=settings.PRESIGNED_URL_EXPIRY)
        return presigned_url

    return None


def verify_exists(session: AWSSession, s3_uri: str) -> bool:
    s3_client = get_s3_client(session)
    try:
        logger.info("Verifying S3 object exists", s3_uri=s3_uri)
        s3_client.head_object(**parse_s3_uri(s3_uri))
        return True
    except s3_client.exceptions.NoSuchKey:
        return False
    except ClientError:
        logger.exception("Failed to verify S3 object exists")
        return False

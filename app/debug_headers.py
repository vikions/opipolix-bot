"""
Debug test - что отправляется в Relayer
"""
import os
import time
from dotenv import load_dotenv
from py_builder_signing_sdk.config import BuilderConfig
from py_builder_signing_sdk.sdk_types import RemoteBuilderConfig

load_dotenv()

BUILDER_SIGNING_URL = os.environ.get("BUILDER_SIGNING_URL")

# Create builder config
remote_config = RemoteBuilderConfig(url=BUILDER_SIGNING_URL)
builder_config = BuilderConfig(remote_builder_config=remote_config)

# Test 1: Generate headers with MILLISECONDS
print("Test 1: Milliseconds timestamp")
timestamp_ms = int(time.time() * 1000)
print(f"Timestamp (ms): {timestamp_ms}")

headers_ms = builder_config.generate_builder_headers(
    method='POST',
    path='/deploy',
    body='',
    timestamp=timestamp_ms
)

if headers_ms:
    print(f"Generated headers:")
    print(f"  API_KEY: {headers_ms.POLY_BUILDER_API_KEY[:20]}...")
    print(f"  TIMESTAMP: {headers_ms.POLY_BUILDER_TIMESTAMP}")
    print(f"  PASSPHRASE: {headers_ms.POLY_BUILDER_PASSPHRASE[:20]}...")
    print(f"  SIGNATURE: {headers_ms.POLY_BUILDER_SIGNATURE[:20]}...")
else:
    print("Failed to generate headers!")

print("\n" + "="*60 + "\n")

# Test 2: Generate headers with SECONDS  
print("Test 2: Seconds timestamp")
timestamp_s = int(time.time())
print(f"Timestamp (s): {timestamp_s}")

headers_s = builder_config.generate_builder_headers(
    method='POST',
    path='/deploy',
    body='',
    timestamp=timestamp_s
)

if headers_s:
    print(f"Generated headers:")
    print(f"  API_KEY: {headers_s.POLY_BUILDER_API_KEY[:20]}...")
    print(f"  TIMESTAMP: {headers_s.POLY_BUILDER_TIMESTAMP}")
    print(f"  PASSPHRASE: {headers_s.POLY_BUILDER_PASSPHRASE[:20]}...")
    print(f"  SIGNATURE: {headers_s.POLY_BUILDER_SIGNATURE[:20]}...")
    
    print(f"\nTimestamp match: {headers_s.POLY_BUILDER_TIMESTAMP} == {timestamp_s}?")
    print(f"Match: {str(headers_s.POLY_BUILDER_TIMESTAMP) == str(timestamp_s)}")
else:
    print("Failed to generate headers!")
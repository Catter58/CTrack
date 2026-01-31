#!/usr/bin/env python
"""
Verify that API documentation generates correctly after router split.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
django.setup()

from api.api import api

# Get the OpenAPI schema
try:
    schema = api.get_openapi_schema()
    print("✓ OpenAPI schema generated successfully")
except Exception as e:
    print(f"✗ Failed to generate OpenAPI schema: {e}")
    sys.exit(1)

# Check that we have paths
if not schema.get("paths"):
    print("✗ No paths found in OpenAPI schema")
    sys.exit(1)

print(f"✓ Found {len(schema['paths'])} API paths")

# Count endpoints by tag
issues_endpoints = []
for path, path_item in schema["paths"].items():
    for method, operation in path_item.items():
        if method in ["get", "post", "put", "patch", "delete"]:
            tags = operation.get("tags", [])
            if "Issues" in tags:
                issues_endpoints.append(f"{method.upper()} {path}")

print(f"\n✓ Found {len(issues_endpoints)} Issues endpoints:")
for endpoint in sorted(issues_endpoints):
    print(f"  - {endpoint}")

# Expected endpoints from the 10 domain routers
expected_endpoints = [
    # issue_types.py (5 endpoints)
    "GET /projects/{key}/issue-types",
    "POST /projects/{key}/issue-types",
    "GET /issue-types/{issue_type_id}",
    "PATCH /issue-types/{issue_type_id}",
    "DELETE /issue-types/{issue_type_id}",
    # statuses.py (5 endpoints)
    "GET /projects/{key}/statuses",
    "POST /projects/{key}/statuses",
    "GET /statuses/{status_id}",
    "PATCH /statuses/{status_id}",
    "DELETE /statuses/{status_id}",
    # issues.py (7 endpoints)
    "GET /issues",
    "POST /projects/{key}/issues",
    "GET /projects/{key}/issues",
    "GET /issues/{issue_key}",
    "GET /issues/{issue_key}/children",
    "PATCH /issues/{issue_key}",
    "DELETE /issues/{issue_key}",
    # comments.py (4 endpoints)
    "GET /issues/{issue_key}/comments",
    "POST /issues/{issue_key}/comments",
    "PATCH /comments/{comment_id}",
    "DELETE /comments/{comment_id}",
    # activity.py (1 endpoint)
    "GET /issues/{issue_key}/activity",
    # workflow.py (4 endpoints)
    "GET /issues/{issue_key}/transitions",
    "POST /issues/{issue_key}/transitions/{transition_id}",
    "PATCH /workflow-transitions/{transition_id}",
    "DELETE /workflow-transitions/{transition_id}",
    # backlog.py (3 endpoints)
    "GET /projects/{key}/backlog",
    "PATCH /issues/{issue_key}/sprint",
    "PATCH /projects/{key}/issues/bulk-update",
    # epics.py (1 endpoint)
    "GET /projects/{key}/epics",
    # attachments.py (4 endpoints)
    "POST /issues/{issue_key}/attachments",
    "GET /issues/{issue_key}/attachments",
    "GET /attachments/{attachment_id}/download",
    "DELETE /attachments/{attachment_id}",
    # editing.py (3 endpoints)
    "POST /issues/{issue_key}/editing",
    "DELETE /issues/{issue_key}/editing",
    "GET /issues/{issue_key}/editing",
]

# Normalize endpoints for comparison (convert to uppercase method + path)
normalized_expected = set(expected_endpoints)
normalized_found = set(issues_endpoints)

# Check if all expected endpoints are present
missing = normalized_expected - normalized_found
extra = normalized_found - normalized_expected

if missing:
    print(f"\n✗ Missing {len(missing)} expected endpoints:")
    for endpoint in sorted(missing):
        print(f"  - {endpoint}")

if extra:
    print(f"\n✓ Found {len(extra)} additional endpoints (might be OK):")
    for endpoint in sorted(extra):
        print(f"  - {endpoint}")

if not missing:
    print("\n✓ All expected Issues endpoints are present!")
    print(f"\n✓ API documentation verification PASSED")
    print(f"  - OpenAPI schema generates successfully")
    print(f"  - All {len(expected_endpoints)} expected Issues endpoints are present")
    print(f"  - All endpoints are tagged correctly with 'Issues'")
    sys.exit(0)
else:
    print(f"\n✗ API documentation verification FAILED")
    sys.exit(1)

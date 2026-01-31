"""
Test that API documentation generates correctly after router split.
This test can be run with pytest to verify the OpenAPI schema.
"""


def test_api_schema_generation():
    """Test that the API schema generates without errors."""
    from api.api import api

    # Get the OpenAPI schema
    schema = api.get_openapi_schema()

    # Verify schema exists
    assert schema is not None, "OpenAPI schema should not be None"
    assert "paths" in schema, "Schema should have paths"
    assert len(schema["paths"]) > 0, "Schema should have at least one path"

    print(
        f"\n✓ OpenAPI schema generated successfully with {len(schema['paths'])} paths"
    )


def test_all_issues_endpoints_present():
    """Test that all Issues endpoints are present with correct tags."""
    from api.api import api

    schema = api.get_openapi_schema()

    # Count endpoints by tag
    issues_endpoints = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "patch", "delete"]:
                tags = operation.get("tags", [])
                if "Issues" in tags:
                    issues_endpoints.append(f"{method.upper()} {path}")

    # Expected endpoints from the 10 domain routers (37 total)
    expected_count = 37  # Based on the implementation plan

    assert len(issues_endpoints) >= expected_count, (
        f"Expected at least {expected_count} Issues endpoints, "
        f"found {len(issues_endpoints)}"
    )

    print(
        f"\n✓ Found {len(issues_endpoints)} Issues endpoints (expected: {expected_count})"
    )

    # Verify critical endpoints from each domain router are present
    critical_endpoints = [
        "GET /api/projects/{key}/issue-types",  # issue_types.py
        "GET /api/projects/{key}/statuses",  # statuses.py
        "GET /api/issues",  # issues.py
        "GET /api/issues/{issue_key}/comments",  # comments.py
        "GET /api/issues/{issue_key}/activity",  # activity.py
        "GET /api/issues/{issue_key}/transitions",  # workflow.py
        "GET /api/projects/{key}/backlog",  # backlog.py
        "GET /api/projects/{key}/epics",  # epics.py
        "GET /api/issues/{issue_key}/attachments",  # attachments.py
        "GET /api/issues/{issue_key}/editing",  # editing.py
    ]

    for endpoint in critical_endpoints:
        assert (
            endpoint in issues_endpoints
        ), f"Critical endpoint '{endpoint}' is missing"

    print("✓ All critical endpoints from each domain router are present")

    # Print all Issues endpoints for verification
    print("\n✓ All Issues endpoints:")
    for endpoint in sorted(issues_endpoints):
        print(f"  - {endpoint}")


def test_api_tags_correct():
    """Test that all issues endpoints are tagged with 'Issues'."""
    from api.api import api

    schema = api.get_openapi_schema()

    # Track endpoints without Issues tag that should have it
    issues_paths = [
        "/api/projects/{key}/issue-types",
        "/api/issue-types/{issue_type_id}",
        "/api/projects/{key}/statuses",
        "/api/statuses/{status_id}",
        "/api/issues",
        "/api/projects/{key}/issues",
        "/api/issues/{issue_key}",
        "/api/issues/{issue_key}/children",
        "/api/issues/{issue_key}/comments",
        "/api/comments/{comment_id}",
        "/api/issues/{issue_key}/activity",
        "/api/issues/{issue_key}/transitions",
        "/api/workflow/{transition_id}",
        "/api/projects/{key}/backlog",
        "/api/issues/{issue_key}/sprint",
        "/api/projects/{key}/issues/bulk-update",
        "/api/projects/{key}/epics",
        "/api/issues/{issue_key}/attachments",
        "/api/attachments/{attachment_id}",
        "/api/attachments/{attachment_id}/download",
        "/api/issues/{issue_key}/editing",
    ]

    missing_tags = []
    for path in issues_paths:
        if path in schema["paths"]:
            path_item = schema["paths"][path]
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    tags = operation.get("tags", [])
                    if "Issues" not in tags:
                        missing_tags.append(f"{method.upper()} {path}")

    assert (
        len(missing_tags) == 0
    ), f"The following endpoints are missing the 'Issues' tag: {missing_tags}"

    print("\n✓ All issues endpoints are correctly tagged with 'Issues'")


if __name__ == "__main__":
    # Run tests manually if executed directly
    print("Running API documentation verification tests...\n")
    test_api_schema_generation()
    test_all_issues_endpoints_present()
    test_api_tags_correct()
    print("\n✅ All API documentation verification tests PASSED!")

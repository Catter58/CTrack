#!/usr/bin/env python
"""
API Authentication Audit Script

Scans all API endpoints to identify their authentication requirements.
Generates a comprehensive report in JSON format.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# Setup Django environment
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ctrack.settings.development")

import django

django.setup()

from api.api import api  # noqa: E402
from apps.users.auth import AuthBearer, AuthQueryToken, OptionalAuthBearer  # noqa: E402


def get_auth_type(auth_instance):
    """
    Determine the authentication type from an auth instance.

    Args:
        auth_instance: The authentication instance or None

    Returns:
        str: Authentication type ('required', 'optional', 'none', 'unknown')
    """
    if auth_instance is None:
        return "none"

    auth_class_name = auth_instance.__class__.__name__

    if isinstance(auth_instance, AuthBearer):
        return "required"
    elif isinstance(auth_instance, OptionalAuthBearer):
        return "optional"
    elif isinstance(auth_instance, AuthQueryToken):
        return "required_query"
    elif auth_class_name == "AuthBearer":
        return "required"
    elif auth_class_name == "OptionalAuthBearer":
        return "optional"
    elif auth_class_name == "AuthQueryToken":
        return "required_query"

    return "unknown"


def audit_api_endpoints():
    """
    Audit all API endpoints for authentication requirements.

    Returns:
        dict: Audit results containing endpoint information and summary
    """
    endpoints = []
    summary = defaultdict(int)

    # Iterate through all registered routers and their operations
    for router_path, router_item in api._routers:
        router = router_item["router"]

        # Check if router has default auth
        router_auth = getattr(router, "auth", None)

        # Iterate through all operations in the router
        for path_operations in router.path_operations.values():
            for operation in path_operations.operations:
                # Determine effective auth (operation auth overrides router auth)
                effective_auth = (
                    operation.auth if hasattr(operation, "auth") else router_auth
                )

                # Handle case where operation.auth is set but we need to check if it's explicitly None
                if hasattr(operation, "auth"):
                    effective_auth = operation.auth
                elif router_auth is not None:
                    effective_auth = router_auth
                else:
                    effective_auth = None

                auth_type = get_auth_type(effective_auth)

                # Build full path
                full_path = f"{router_path}{operation.path}"

                endpoint_info = {
                    "method": operation.methods[0] if operation.methods else "GET",
                    "path": full_path,
                    "auth_type": auth_type,
                    "auth_class": (
                        effective_auth.__class__.__name__
                        if effective_auth is not None
                        else None
                    ),
                    "summary": getattr(operation, "summary", None),
                    "description": getattr(operation, "description", None),
                }

                endpoints.append(endpoint_info)
                summary[auth_type] += 1

    # Sort endpoints by path and method
    endpoints.sort(key=lambda x: (x["path"], x["method"]))

    return {
        "total_endpoints": len(endpoints),
        "summary": dict(summary),
        "endpoints": endpoints,
    }


def verify_auth_enforcement(results):
    """
    Verify that all endpoints have explicit auth configuration.

    Args:
        results: Audit results from audit_api_endpoints()

    Returns:
        bool: True if all endpoints have explicit auth, False otherwise
    """
    print("Starting authentication enforcement verification...")

    # Check for endpoints with unknown auth type (indicates missing explicit auth)
    unknown_endpoints = [e for e in results["endpoints"] if e["auth_type"] == "unknown"]

    # Check for endpoints with "none" auth type (might need to be explicitly configured)
    none_endpoints = [e for e in results["endpoints"] if e["auth_type"] == "none"]

    # Expected public endpoints that should not require auth
    public_expected = [
        "/api/health",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
    ]

    # Find endpoints with no auth that are not in the expected public list
    unexpected_public = [
        e
        for e in none_endpoints
        if not any(e["path"].startswith(expected) for expected in public_expected)
    ]

    verification_passed = True

    # Report findings
    print(f"\nTotal endpoints: {results['total_endpoints']}")
    print(
        f"Endpoints with explicit auth: {results['total_endpoints'] - len(unknown_endpoints)}"
    )

    if unknown_endpoints:
        print(
            f"\n❌ FAIL: Found {len(unknown_endpoints)} endpoints with unknown auth type:"
        )
        for endpoint in unknown_endpoints:
            print(f"  {endpoint['method']:6} {endpoint['path']}")
        verification_passed = False

    if unexpected_public:
        print(
            f"\n❌ FAIL: Found {len(unexpected_public)} endpoints without explicit auth configuration:"
        )
        for endpoint in unexpected_public:
            print(f"  {endpoint['method']:6} {endpoint['path']}")
        verification_passed = False

    if verification_passed:
        print("\n✅ PASS: All endpoints have explicit auth configuration")
        print(f"  - Required auth: {results['summary'].get('required', 0)}")
        print(f"  - Optional auth: {results['summary'].get('optional', 0)}")
        print(f"  - Query token auth: {results['summary'].get('required_query', 0)}")
        print(
            f"  - Public (explicitly configured): {len(none_endpoints) - len(unexpected_public)}"
        )

    return verification_passed


def main():
    """Main function to run the audit and generate report."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="API Authentication Audit Script")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify that all endpoints have explicit auth configuration and exit",
    )
    args = parser.parse_args()

    # Run the audit
    results = audit_api_endpoints()

    # If verify mode, run verification and exit
    if args.verify:
        success = verify_auth_enforcement(results)
        sys.exit(0 if success else 1)

    # Otherwise, run full audit report
    print("Starting API authentication audit...")

    # Print summary to console
    print("\n=== Authentication Audit Summary ===")
    print(f"Total endpoints: {results['total_endpoints']}")
    print("\nBy authentication type:")
    for auth_type, count in results["summary"].items():
        print(f"  {auth_type}: {count}")

    # Generate detailed report
    print("\n=== Endpoints by Authentication Type ===")

    # Group endpoints by auth type for display
    by_auth_type = defaultdict(list)
    for endpoint in results["endpoints"]:
        by_auth_type[endpoint["auth_type"]].append(endpoint)

    for auth_type, endpoints in sorted(by_auth_type.items()):
        print(f"\n{auth_type.upper()} ({len(endpoints)} endpoints):")
        for endpoint in endpoints:
            print(f"  {endpoint['method']:6} {endpoint['path']}")

    # Write JSON report
    output_file = Path(__file__).parent.parent / "auth_audit_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Detailed report written to: {output_file}")

    # Highlight potential security issues
    if results["summary"].get("none", 0) > 0:
        none_endpoints = [e for e in results["endpoints"] if e["auth_type"] == "none"]
        public_expected = [
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
        ]
        unexpected_public = [
            e
            for e in none_endpoints
            if not any(e["path"].startswith(expected) for expected in public_expected)
        ]

        if unexpected_public:
            print(
                f"\n⚠️  WARNING: Found {len(unexpected_public)} endpoints without authentication:"
            )
            for endpoint in unexpected_public:
                print(f"  {endpoint['method']:6} {endpoint['path']}")

    if results["summary"].get("unknown", 0) > 0:
        print(
            f"\n⚠️  WARNING: Found {results['summary']['unknown']} endpoints with unknown auth type"
        )

    print("\n✓ Audit complete")


if __name__ == "__main__":
    main()

#!/bin/bash
# Verify all API routers can be imported

echo "Verifying API router imports..."
echo ""

# Check if we can import each router
routers=(
    "api.issues.issue_types"
    "api.issues.statuses"
    "api.issues.issues"
    "api.issues.comments"
    "api.issues.activity"
    "api.issues.workflow"
    "api.issues.backlog"
    "api.issues.epics"
    "api.issues.attachments"
    "api.issues.editing"
)

failed=0
for router in "${routers[@]}"; do
    echo -n "Checking $router... "
    if python3 -c "import sys; sys.path.insert(0, 'backend'); from $router import router; print('OK')" 2>/dev/null; then
        echo "✓"
    else
        echo "✗ FAILED"
        failed=$((failed + 1))
    fi
done

echo ""
echo -n "Checking main API (api.api)... "
if python3 -c "import sys; sys.path.insert(0, 'backend'); from api.api import api; print('OK')" 2>/dev/null; then
    echo "✓"
else
    echo "✗ FAILED"
    failed=$((failed + 1))
fi

echo ""
if [ $failed -eq 0 ]; then
    echo "✅ All imports successful!"
    exit 0
else
    echo "❌ $failed import(s) failed"
    exit 1
fi

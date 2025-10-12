"""Diagnose import issues step by step."""

import sys
sys.path.insert(0, '/app')

print("Step 1: Import admin_auth router")
try:
    from src.api.v1.admin_auth import router as admin_auth_router
    print(f"✅ admin_auth_router: {admin_auth_router}")
    print(f"   Prefix: {admin_auth_router.prefix}")
    print(f"   Routes: {len(admin_auth_router.routes)}")
    for route in admin_auth_router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f"     {list(route.methods)} {route.path}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 2: Import api_router")
try:
    from src.api.v1 import api_router
    print(f"✅ api_router: {api_router}")
    print(f"   Prefix: {api_router.prefix if hasattr(api_router, 'prefix') else 'None'}")
    print(f"   Routes: {len(api_router.routes)}")
    for route in api_router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f"     {list(route.methods)} {route.path}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Create FastAPI app and register routes")
try:
    from src.main import create_app
    app = create_app()
    print(f"✅ App created: {app.title}")
    print(f"   Total routes: {len(app.routes)}")

    admin_routes = [r for r in app.routes if hasattr(r, 'path') and 'admin' in r.path]
    print(f"\n   Admin routes found: {len(admin_routes)}")
    for route in admin_routes:
        if hasattr(route, 'methods'):
            print(f"     {list(route.methods)} {route.path}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All imports successful!")

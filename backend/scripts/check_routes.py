"""Check if routes are properly registered."""

import sys
sys.path.insert(0, '/app')

try:
    print("=== Importing main app ===")
    from src.main import app

    print("\n=== All registered routes ===")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            print(f"{list(route.methods)} {route.path}")

    print("\n=== Checking admin routes ===")
    admin_routes = [r for r in app.routes if hasattr(r, 'path') and '/admin' in r.path]
    if admin_routes:
        print(f"✅ Found {len(admin_routes)} admin routes")
        for route in admin_routes:
            if hasattr(route, 'methods'):
                print(f"  {list(route.methods)} {route.path}")
    else:
        print("❌ No admin routes found!")

    print("\n=== Checking API router import ===")
    try:
        from src.api.v1 import api_router
        print(f"✅ api_router imported: {api_router}")
        print(f"   api_router routes: {len(api_router.routes)}")
    except Exception as e:
        print(f"❌ Failed to import api_router: {e}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

"""Manual API testing script for Admin Authentication endpoints.

Usage:
    docker run --rm --network host -v "$(pwd):/app" -w /app python:3.11-slim \
        bash -c "pip install -q requests && python scripts/test_admin_api.py"
"""

import json
import sys
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    print("❌ requests library not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests


class AdminAPITester:
    """Test Admin Authentication API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize tester with base URL.

        Args:
            base_url: API base URL (default: http://localhost:8000)
        """
        self.base_url = base_url
        self.access_token: Optional[str] = None

    def print_response(self, title: str, response: requests.Response) -> None:
        """Pretty print API response.

        Args:
            title: Test title
            response: HTTP response object
        """
        print(f"\n{'='*60}")
        print(f"📝 {title}")
        print(f"{'='*60}")
        print(f"Status Code: {response.status_code}")
        print(f"URL: {response.request.method} {response.url}")

        try:
            data = response.json()
            print(f"\nResponse Body:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # Extract token if present
            if "access_token" in data:
                self.access_token = data["access_token"]
                print(f"\n✅ Access token saved for subsequent requests")

        except json.JSONDecodeError:
            print(f"\nResponse Text: {response.text}")

    def test_health(self) -> bool:
        """Test health check endpoint.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            self.print_response("Health Check", response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

    def test_login(self, username: str = "superadmin", password: str = "admin123456") -> bool:
        """Test admin login endpoint.

        Args:
            username: Admin username
            password: Admin password

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/admin/login",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            self.print_response(f"Admin Login (username={username})", response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Login test failed: {e}")
            return False

    def test_get_current_user(self) -> bool:
        """Test get current admin info endpoint.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return False

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/me",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=5,
            )
            self.print_response("Get Current Admin Info", response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Get current user test failed: {e}")
            return False

    def test_refresh_token(self) -> bool:
        """Test token refresh endpoint.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/admin/refresh",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=5,
            )
            self.print_response("Refresh Access Token", response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Token refresh test failed: {e}")
            return False

    def test_change_password(
        self,
        old_password: str = "admin123456",
        new_password: str = "new_password_123"
    ) -> bool:
        """Test change password endpoint.

        Args:
            old_password: Current password
            new_password: New password

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/admin/change-password",
                json={"old_password": old_password, "new_password": new_password},
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=5,
            )
            self.print_response("Change Password", response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Change password test failed: {e}")
            return False

    def test_logout(self) -> bool:
        """Test admin logout endpoint.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/admin/logout",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=5,
            )
            self.print_response("Admin Logout", response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Logout test failed: {e}")
            return False

    def run_all_tests(self) -> None:
        """Run all API tests in sequence."""
        print("\n" + "="*60)
        print("🚀 Admin Authentication API Test Suite")
        print("="*60)

        results = {}

        # Test 1: Health check
        results["health"] = self.test_health()

        # Test 2: Login
        results["login"] = self.test_login()

        # Test 3: Get current user (requires login)
        results["get_user"] = self.test_get_current_user()

        # Test 4: Refresh token (requires login)
        results["refresh"] = self.test_refresh_token()

        # Test 5: Logout
        results["logout"] = self.test_logout()

        # Print summary
        print("\n" + "="*60)
        print("📊 Test Results Summary")
        print("="*60)

        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {test_name}")

        total = len(results)
        passed = sum(1 for v in results.values() if v)
        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            sys.exit(1)


def main():
    """Main entry point."""
    # You can change the base URL here if needed
    base_url = "http://localhost:8000"

    tester = AdminAPITester(base_url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()

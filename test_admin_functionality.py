#!/usr/bin/env python3
"""
Test script to verify admin user management functionality.
This demonstrates how admins can create new users for the platform.
"""

import requests
import json

# Server configuration
BASE_URL = "http://localhost:8002"

def test_user_management():
    """Test admin user creation and management functionality."""
    
    print("=== Testing Admin User Management Functionality ===\n")
    
    # 1. Test getting current users
    print("1. Getting current authorized users...")
    try:
        response = requests.get(f"{BASE_URL}/api/users")
        if response.status_code == 200:
            users_data = response.json()
            print(f"✅ Current users data: {json.dumps(users_data, indent=2)}")
            print(f"📊 Admins: {users_data['admins']}")
            print(f"👥 Regular users: {users_data['regular_users']}")
            print(f"🔍 All users: {users_data['all_users']}")
        else:
            print(f"❌ Failed to get users: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return False
    
    print("\n" + "="*50)
    
    # 2. Test creating a new user (admin functionality)
    print("2. Testing user creation by admin...")
    new_username = "TESTUSER"
    admin_username = "EMIN"  # Using EMIN as admin
    
    create_data = {
        "username": new_username,
        "admin_username": admin_username
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/users", json=create_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User creation successful: {result}")
        else:
            print(f"⚠️  User creation response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error creating user: {e}")
    
    print("\n" + "="*50)
    
    # 3. Verify the new user appears in the users list
    print("3. Verifying new user appears in authorized users list...")
    try:
        response = requests.get(f"{BASE_URL}/api/users")
        if response.status_code == 200:
            updated_users = response.json()
            if new_username in updated_users['all_users']:
                print(f"✅ New user '{new_username}' successfully added to authorized users!")
                print(f"📋 Updated user list: {updated_users['all_users']}")
            else:
                print(f"⚠️  New user '{new_username}' not found in user list")
        else:
            print(f"❌ Failed to verify users: {response.status_code}")
    except Exception as e:
        print(f"❌ Error verifying users: {e}")
    
    print("\n" + "="*50)
    
    # 4. Test deleting the test user (cleanup)
    print("4. Cleaning up - deleting test user...")
    try:
        response = requests.delete(f"{BASE_URL}/api/users/{new_username}?admin_username={admin_username}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ User deletion successful: {result}")
        else:
            print(f"⚠️  User deletion response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
    
    print("\n" + "="*50)
    print("🎉 Admin user management test completed!")
    print("\n📝 INSTRUCTIONS FOR ADMINS:")
    print("1. Go to http://localhost:8002 for the login page")
    print("2. Login with admin credentials (EMIN, ETHMAN, ZAIN, or MOUHAMEDOU)")
    print("3. Navigate to the 'Admin' tab in the dashboard")
    print("4. Use 'Add New User' section to create accounts for new team members")
    print("5. New users will immediately appear on the login page for everyone")
    print("6. Users can be removed from the same Admin panel if needed")

if __name__ == "__main__":
    test_user_management()

#!/usr/bin/env python3
"""Test API endpoints directly."""

import requests
import json
from datetime import datetime

def test_api():
    base_url = "http://127.0.0.1:5001"
    
    print("🧪 Testing FPL AI Optimizer API")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Get Players
    print("\n2. Testing Get Players...")
    try:
        response = requests.get(f"{base_url}/api/players?limit=5")
        print(f"   Status: {response.status_code}")
        data = response.json()
        if data.get('success'):
            print(f"   Found {len(data['data']['players'])} players")
        else:
            print(f"   Error: {data.get('error')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Team Optimization
    print("\n3. Testing Team Optimization...")
    try:
        payload = {
            "budget": 100.0,
            "formation": None,
            "max_players_per_team": 3
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{base_url}/api/optimize", 
            data=json.dumps(payload),
            headers=headers
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success'):
                    print("   ✅ Optimization successful!")
                    team = data.get('data', {})
                    print(f"   Team size: {len(team.get('players', []))}")
                    print(f"   Total cost: £{team.get('total_cost', 0)}M")
                    print(f"   Expected points: {team.get('total_expected_points', 0)}")
                else:
                    print(f"   ❌ API Error: {data.get('error')}")
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON Parse Error: {e}")
                print(f"   Raw response: {response.text[:200]}...")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ❌ Request Error: {e}")
    
    print(f"\n🏁 API Test completed at {datetime.now()}")

if __name__ == '__main__':
    test_api()
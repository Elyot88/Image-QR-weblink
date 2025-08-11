#!/usr/bin/env python3
"""
Additional Backend API Tests for Edge Cases
"""

import requests
import json
import os
import io
from PIL import Image
import tempfile

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_BASE = f"{BASE_URL}/api"

print(f"Testing additional edge cases at: {API_BASE}")

def create_large_image():
    """Create a large image to test file size limits"""
    img = Image.new('RGB', (3000, 3000), (255, 0, 0))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', quality=95)
    img_bytes.seek(0)
    return img_bytes

def create_png_image():
    """Create a PNG image to test different formats"""
    img = Image.new('RGB', (100, 100), (0, 255, 0))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_png_upload():
    """Test uploading PNG image"""
    print("\n=== Testing PNG Image Upload ===")
    
    png_image = create_png_image()
    files = {
        'file': ('test.png', png_image, 'image/png')
    }
    data = {
        'url': 'https://example.com/png-test'
    }
    
    try:
        response = requests.post(f"{API_BASE}/link-image", files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ PNG upload test passed")
            return response.json().get('image_id')
        else:
            print(f"❌ PNG upload test failed - Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ PNG upload test failed with exception: {e}")
        return None

def test_large_image_upload():
    """Test uploading a large image"""
    print("\n=== Testing Large Image Upload ===")
    
    large_image = create_large_image()
    files = {
        'file': ('large.jpg', large_image, 'image/jpeg')
    }
    data = {
        'url': 'https://example.com/large-test'
    }
    
    try:
        response = requests.post(f"{API_BASE}/link-image", files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Large image upload test passed")
            return True
        elif response.status_code == 413:
            print("✅ Large image upload test passed - Correctly rejected as too large")
            return True
        else:
            print(f"❌ Large image upload test failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Large image upload test failed with exception: {e}")
        return False

def test_missing_url_parameter():
    """Test uploading image without URL parameter"""
    print("\n=== Testing Missing URL Parameter ===")
    
    test_image = Image.new('RGB', (100, 100), (255, 0, 0))
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {
        'file': ('test.jpg', img_bytes, 'image/jpeg')
    }
    # No URL parameter provided
    
    try:
        response = requests.post(f"{API_BASE}/link-image", files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 422:  # Validation error
            print("✅ Missing URL parameter test passed - Correctly rejected")
            return True
        else:
            print(f"❌ Missing URL parameter test failed - Should have returned 422, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Missing URL parameter test failed with exception: {e}")
        return False

def test_missing_file_parameter():
    """Test request without file parameter"""
    print("\n=== Testing Missing File Parameter ===")
    
    data = {
        'url': 'https://example.com/test'
    }
    # No file parameter provided
    
    try:
        response = requests.post(f"{API_BASE}/link-image", data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 422:  # Validation error
            print("✅ Missing file parameter test passed - Correctly rejected")
            return True
        else:
            print(f"❌ Missing file parameter test failed - Should have returned 422, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Missing file parameter test failed with exception: {e}")
        return False

def test_scan_with_custom_threshold():
    """Test scanning with different threshold values"""
    print("\n=== Testing Scan with Custom Threshold ===")
    
    # First link an image
    test_image = Image.new('RGB', (100, 100), (128, 128, 128))
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    files = {
        'file': ('threshold_test.jpg', img_bytes, 'image/jpeg')
    }
    data = {
        'url': 'https://example.com/threshold-test'
    }
    
    link_response = requests.post(f"{API_BASE}/link-image", files=files, data=data)
    if link_response.status_code != 200:
        print("❌ Failed to link image for threshold test")
        return False
    
    # Now scan with very strict threshold
    similar_image = Image.new('RGB', (100, 100), (130, 130, 130))  # Slightly different
    scan_bytes = io.BytesIO()
    similar_image.save(scan_bytes, format='JPEG')
    scan_bytes.seek(0)
    
    scan_files = {
        'file': ('scan_threshold.jpg', scan_bytes, 'image/jpeg')
    }
    scan_data = {
        'threshold': '1'  # Very strict threshold
    }
    
    try:
        response = requests.post(f"{API_BASE}/scan-image", files=scan_files, data=scan_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Custom threshold test passed - Status: {result.get('status')}")
            return True
        else:
            print(f"❌ Custom threshold test failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Custom threshold test failed with exception: {e}")
        return False

def test_update_existing_image_url():
    """Test updating URL for an existing image"""
    print("\n=== Testing Update Existing Image URL ===")
    
    # Create a unique image
    test_image = Image.new('RGB', (100, 100), (200, 100, 50))
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    # First upload
    files = {
        'file': ('update_test.jpg', img_bytes, 'image/jpeg')
    }
    data = {
        'url': 'https://example.com/original-url'
    }
    
    first_response = requests.post(f"{API_BASE}/link-image", files=files, data=data)
    if first_response.status_code != 200:
        print("❌ Failed to link image for update test")
        return False
    
    first_result = first_response.json()
    original_id = first_result.get('image_id')
    
    # Upload same image with different URL
    img_bytes.seek(0)  # Reset stream
    files = {
        'file': ('update_test.jpg', img_bytes, 'image/jpeg')
    }
    data = {
        'url': 'https://example.com/updated-url'
    }
    
    try:
        response = requests.post(f"{API_BASE}/link-image", files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'updated' and result.get('image_id') == original_id:
                print("✅ Update existing image URL test passed")
                return True
            else:
                print("❌ Update existing image URL test failed - Unexpected response")
                return False
        else:
            print(f"❌ Update existing image URL test failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Update existing image URL test failed with exception: {e}")
        return False

def run_additional_tests():
    """Run all additional edge case tests"""
    print("🔍 Starting Additional Backend Edge Case Tests")
    print("=" * 60)
    
    test_results = {}
    
    # Test different image formats
    test_results['png_upload'] = test_png_upload() is not None
    
    # Test large image handling
    test_results['large_image'] = test_large_image_upload()
    
    # Test missing parameters
    test_results['missing_url'] = test_missing_url_parameter()
    test_results['missing_file'] = test_missing_file_parameter()
    
    # Test custom threshold
    test_results['custom_threshold'] = test_scan_with_custom_threshold()
    
    # Test URL update
    test_results['update_url'] = test_update_existing_image_url()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ADDITIONAL TESTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            passed += 1
    
    print(f"\nAdditional Tests: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
    
    return test_results

if __name__ == "__main__":
    run_additional_tests()
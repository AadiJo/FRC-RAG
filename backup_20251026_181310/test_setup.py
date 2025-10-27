#!/usr/bin/env python3
"""
Quick test to make sure all my server parts are working
"""

import sys
import os
import importlib.util

def test_imports():
    """Make sure I can load all the modules"""
    print("🧪 Testing imports...")
    
    try:
        # Add src to path so I can import stuff
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        
        # Try importing the core modules
        from src.server.config import get_config
        from src.server.rate_limiter import RateLimiter
        from src.server.ollama_proxy import OllamaProxy
        from src.server.tunnel import TunnelManager
        
        print("✅ All imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Make sure my config loads properly"""
    print("🔧 Testing configuration...")
    
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        from src.server.config import get_config
        
        Config = get_config()
        config_dict = Config.to_dict()
        
        print(f"✅ Configuration loaded")
        print(f"   Environment: {Config.ENVIRONMENT}")
        print(f"   Server: {Config.HOST}:{Config.PORT}")
        print(f"   Ollama: {Config.get_ollama_url()}")
        print(f"   Rate limit: {Config.RATE_LIMIT_REQUESTS} req/{Config.RATE_LIMIT_WINDOW}min")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_rate_limiter():
    """Make sure rate limiting works"""
    print("🚦 Testing rate limiter...")
    
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        from src.server.rate_limiter import RateLimiter
        
        # Set up a rate limiter with small limits for testing
        limiter = RateLimiter(max_requests=2, window_minutes=1)
        
        # Test with a fake client
        client_id = "test_client"
        
        # First request should work
        assert limiter.is_allowed(client_id), "First request should be allowed"
        
        # Second request should work
        assert limiter.is_allowed(client_id), "Second request should be allowed"
        
        # Third request should fail
        assert not limiter.is_allowed(client_id), "Third request should be denied"
        
        # Check how many requests are left
        remaining = limiter.get_remaining_requests(client_id)
        assert remaining == 0, f"Should have 0 remaining requests, got {remaining}"
        
        print("✅ Rate limiter working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiter error: {e}")
        return False

def main():
    """Run all my tests"""
    print("🔍 FRC RAG Server Component Tests")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_config, 
        test_rate_limiter
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            print()
    
    print("=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! Server components are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
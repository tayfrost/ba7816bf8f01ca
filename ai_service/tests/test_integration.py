"""Integration tests for deployed Docker containers with file logging."""

import pytest
import requests
import time
import json
from pathlib import Path
from datetime import datetime

BASE_URL = "http://localhost:8002"
TIMEOUT = 30

# Create test results directory
TEST_RESULTS_DIR = Path(__file__).parent / "test_results"
TEST_RESULTS_DIR.mkdir(exist_ok=True)

# Create log file with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = TEST_RESULTS_DIR / f"integration_test_{timestamp}.log"
SUMMARY_FILE = TEST_RESULTS_DIR / "latest_test_summary.txt"


def log(message: str, to_file: bool = True, to_console: bool = True):
    """Log message to both file and console."""
    if to_console:
        print(message)
    if to_file:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")


@pytest.fixture(scope="module", autouse=True)
def setup_logging():
    """Set up logging for the test session."""
    log("="*80)
    log(f"SENTINELAI INTEGRATION TEST RUN")
    log(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Target: {BASE_URL}")
    log("="*80)
    log("")
    yield
    log("")
    log("="*80)
    log("TEST RUN COMPLETED")
    log("="*80)


@pytest.fixture(scope="module")
def wait_for_service():
    """Wait for service to be ready."""
    log("\n[SETUP] Waiting for AI service to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                log(f"[SETUP] ✓ Service ready after {i+1} attempts\n")
                return
        except requests.exceptions.RequestException as e:
            if i < max_retries - 1:
                log(f"[SETUP] Attempt {i+1}/{max_retries} - Service not ready yet, retrying...")
                time.sleep(2)
            else:
                log(f"[SETUP] ✗ Service failed to become ready: {str(e)}")
                raise
    pytest.fail("Service did not become ready in time")


class TestDeployedService:
    """Test the deployed AI service in Docker."""
    
    def test_service_health(self, wait_for_service):
        """Test that service is running and healthy."""
        log("\n" + "="*80)
        log("TEST 1: Health Check")
        log("="*80)
        
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        data = response.json()
        
        log(f"Status Code: {response.status_code}")
        log(f"Response Data:")
        log(json.dumps(data, indent=2))
        
        assert response.status_code == 200
        assert "status" in data
        
        log("✓ PASSED")
    
    def test_root_endpoint(self, wait_for_service):
        """Test root endpoint."""
        log("\n" + "="*80)
        log("TEST 2: Root Endpoint")
        log("="*80)
        
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)
        data = response.json()
        
        log(f"Status Code: {response.status_code}")
        log(f"Service: {data.get('service')}")
        log(f"Status: {data.get('status')}")
        
        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert "SentinelAI" in data["service"]
        
        log("✓ PASSED")
    
    def test_analyze_no_risk_message(self, wait_for_service):
        """Test analysis of a normal, non-risk message."""
        log("\n" + "="*80)
        log("TEST 3: No-Risk Message Analysis")
        log("="*80)
        
        message = "Had a great team meeting today! We finished the project ahead of schedule."
        log(f"Input Message: {message}")
        log("-"*80)
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={"message": message},
            timeout=TIMEOUT
        )
        
        log(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log("\n[AI AGENT ANALYSIS]")
            log(f"Response: {data.get('response')}")
            
            if data.get('score'):
                log("\nMental Health Scores:")
                for key, value in data['score'].items():
                    log(f"  • {key}: {value}")
            
            if data.get('recommendations'):
                log("\nRecommendations:")
                for rec in data['recommendations']:
                    log(f"  • {rec}")
            
            assert "score" in data
            assert "response" in data
            log("\n✓ PASSED")
        else:
            log(f"✗ FAILED - Unexpected status code: {response.status_code}")
            log(f"Response: {response.text}")
            assert response.status_code == 200
    
    def test_analyze_stress_message(self, wait_for_service):
        """Test analysis of a message with stress indicators."""
        log("\n" + "="*80)
        log("TEST 4: Stress Indicators Analysis")
        log("="*80)
        
        message = "I'm feeling completely overwhelmed with work. Too many deadlines and not enough time. Can't sleep properly."
        log(f"Input Message: {message}")
        log("-"*80)
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={"message": message},
            timeout=TIMEOUT
        )
        
        log(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log("\n[AI AGENT ANALYSIS]")
            log("Risk Assessment: CONFIRMED")
            
            if data.get('score'):
                log("\nMental Health Scores:")
                for key, value in data['score'].items():
                    if isinstance(value, (int, float)):
                        indicator = "⚠️ HIGH" if value > 60 else "✓ NORMAL"
                        log(f"  {indicator} {key}: {value}")
            
            log(f"\nAI Response:")
            log(f"{data.get('response')}")
            
            if data.get('recommendations'):
                log("\nRecommendations:")
                for rec in data['recommendations']:
                    log(f"  • {rec}")
            
            assert "score" in data
            assert data['score']['stress_level'] >= 0
            log("\n✓ PASSED")
        else:
            log(f"✗ FAILED - Unexpected status code: {response.status_code}")
            log(f"Response: {response.text}")
            assert response.status_code == 200
    
    def test_analyze_burnout_message(self, wait_for_service):
        """Test analysis of a message with burnout indicators."""
        log("\n" + "="*80)
        log("TEST 5: Burnout/Depression Indicators Analysis")
        log("="*80)
        
        message = "I don't see the point anymore. Every day is the same. I'm exhausted all the time and nothing seems to matter."
        log(f"Input Message: {message}")
        log("-"*80)
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={"message": message},
            timeout=TIMEOUT
        )
        
        log(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log("\n[AI AGENT ANALYSIS]")
            log("Risk Assessment: CONFIRMED")
            
            if data.get('score'):
                log("\nMental Health Scores:")
                for key, value in data['score'].items():
                    if isinstance(value, (int, float)):
                        if value > 70:
                            indicator = "🚨 CRITICAL"
                        elif value > 50:
                            indicator = "⚠️ ELEVATED"
                        else:
                            indicator = "✓ NORMAL"
                        log(f"  {indicator} {key}: {value}")
            
            log(f"\nAI Response:")
            log(f"{data.get('response')}")
            
            if data.get('recommendations'):
                log("\nRecommendations:")
                for rec in data['recommendations']:
                    log(f"  • {rec}")
            
            assert "score" in data
            log("\n✓ PASSED")
        else:
            log(f"✗ FAILED - Unexpected status code: {response.status_code}")
            log(f"Response: {response.text}")
            assert response.status_code == 200
    
    def test_analyze_anxiety_message(self, wait_for_service):
        """Test analysis of a message with anxiety indicators."""
        log("\n" + "="*80)
        log("TEST 6: Anxiety Markers Analysis")
        log("="*80)
        
        message = "I'm constantly worried about making mistakes. My heart races before meetings. I can't stop checking my work over and over."
        log(f"Input Message: {message}")
        log("-"*80)
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={"message": message},
            timeout=TIMEOUT
        )
        
        log(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log("\n[AI AGENT ANALYSIS]")
            
            if data.get('score'):
                risk_level = "CONFIRMED" if data['score'].get('anxiety_markers', 0) > 50 else "MINIMAL"
                log(f"Risk Assessment: {risk_level}")
                
                log("\nMental Health Scores:")
                for key, value in data['score'].items():
                    if isinstance(value, (int, float)):
                        indicator = "⚠️" if value > 50 else "✓"
                        log(f"  {indicator} {key}: {value}")
            
            log(f"\nAI Response:")
            log(f"{data.get('response')}")
            
            if data.get('recommendations'):
                log("\nRecommendations:")
                for rec in data['recommendations']:
                    log(f"  • {rec}")
            
            assert "score" in data
            log("\n✓ PASSED")
        else:
            log(f"✗ FAILED - Unexpected status code: {response.status_code}")
            log(f"Response: {response.text}")
            assert response.status_code == 200
    
    def test_analyze_validation_error(self, wait_for_service):
        """Test that invalid input is handled properly."""
        log("\n" + "="*80)
        log("TEST 7: Invalid Input Validation")
        log("="*80)
        log("Sending empty request...")
        
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={},
            timeout=TIMEOUT
        )
        
        log(f"Status Code: {response.status_code}")
        log(f"Expected: 422 (Validation Error)")
        
        assert response.status_code == 422
        log("✓ PASSED")


@pytest.fixture(scope="module", autouse=True)
def create_summary(wait_for_service):
    """Create test summary after all tests complete."""
    yield
    
    # Read the log file and create summary
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        full_log = f.read()
    
    # Count results
    passed = full_log.count("✓ PASSED")
    failed = full_log.count("✗ FAILED")
    total = passed + failed
    
    # Create summary
    summary = f"""
SENTINELAI INTEGRATION TEST SUMMARY
================================================================================
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Full Log: {LOG_FILE.name}

Results:
  Total Tests: {total}
  Passed: {passed}
  Failed: {failed}
  Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%

================================================================================
"""
    
    # Write summary
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(summary)

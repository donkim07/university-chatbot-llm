import requests
import json
import sys

BACKEND_URL = "http://localhost:8000"

def test_health():
    print("=== Testing /health endpoint ===")
    try:
        res = requests.get(f"{BACKEND_URL}/health", timeout=5.0)
        print(f"Status Code: {res.status_code}")
        print("Response JSON:")
        print(json.dumps(res.json(), indent=2))
        print("Health Check PASSED.\n")
        return res.json().get("llm_connected", False)
    except Exception as e:
        print(f"Health Check FAILED: {str(e)}\n")
        return False

def test_ask(question: str):
    print(f"=== Testing /ask endpoint with: '{question}' ===")
    try:
        res = requests.post(
            f"{BACKEND_URL}/ask",
            json={"question": question},
            timeout=65.0
        )
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            print("Response JSON:")
            print(json.dumps(res.json(), indent=2))
            print("Ask Endpoint PASSED.\n")
        else:
            print(f"Response Error: {res.text}")
            print("Ask Endpoint FAILED.\n")
    except Exception as e:
        print(f"Ask Endpoint FAILED: {str(e)}\n")

def test_empty_question():
    print("=== Testing /ask endpoint with empty question (Validation) ===")
    try:
        res = requests.post(
            f"{BACKEND_URL}/ask",
            json={"question": "   "},
            timeout=5.0
        )
        print(f"Status Code: {res.status_code} (Expected: 400)")
        print(f"Response Content: {res.text}")
        if res.status_code == 400:
            print("Empty Question Validation PASSED.\n")
        else:
            print("Empty Question Validation FAILED.\n")
    except Exception as e:
        print(f"Empty Question Validation FAILED: {str(e)}\n")

if __name__ == "__main__":
    print("Starting Automated API Integration Tests...\n")
    
    # 1. Test health check
    llm_connected = test_health()
    
    # 2. Test standard queries
    test_ask("When is the deadline to register for classes?")
    test_ask("How many library books can I borrow?")
    test_ask("What are the codes and rules for cheating in exams?")
    
    # 3. Test empty input handling
    test_empty_question()
    
    print("Testing Completed.")

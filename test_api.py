import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("Testing API endpoints...")
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    print("Health check passed")
    files = {'file': open('test_document.txt', 'rb')}
    response = requests.post(f"{BASE_URL}/api/upload", files=files)
    assert response.status_code == 200
    case_id = response.json()['case_id']
    print(f"File uploaded: {case_id}")
    time.sleep(5)
    response = requests.post(
        f"{BASE_URL}/api/summarize",
        json={'case_id': case_id}
    )
    assert response.status_code == 200
    print("Summary retrieved")
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={
            'case_id': case_id,
            'query': 'Show witness information'
        }
    )
    assert response.status_code == 200
    print("Query answered")
    response = requests.get(f"{BASE_URL}/api/analytics")
    assert response.status_code == 200
    print("Analytics retrieved")
    print("All tests passed!")

if __name__ == '__main__':
    test_api()

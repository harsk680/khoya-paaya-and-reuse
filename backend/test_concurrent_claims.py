
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

URL = "http://127.0.0.1:8000/api/claim"

# Add fresh JWT tokens locally. Never share them.
TOKEN_STUDENT_1 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJlbWFpbCI6ImhhcnNoaXQzQHRlc3QuY29tIiwicm9sZSI6InN0dWRlbnQiLCJleHAiOjE3OTUwODc1MjN9.PHRi4S9dXJH-uu0h-_d6w-TY5KUhCFx-KFjnG2gNTZA"
TOKEN_STUDENT_2 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjozLCJlbWFpbCI6ImFrc2hhdEAuY29tIiwicm9sZSI6ImF1dGhvcml0eSIsImV4cCI6MTc5NTA4NzYwM30.IsEyzdP12apiodWPwFAW-KQTHu6Ui3laPOzN0HDtzE8"

# Change this to the NEW found_id created for testing.
TEST_FOUND_ID = 0



def submit_claim(token, student):
    data = json.dumps({"found_id": 4}).encode("utf-8")

    request = urllib.request.Request(
        URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode())
            return student, response.status, result

    except urllib.error.HTTPError as error:
        return student, error.code, error.read().decode()


with ThreadPoolExecutor(max_workers=2) as executor:

    futures = [
    executor.submit(
        submit_claim,
        TOKEN_STUDENT_1,
        "Student 1"
    ),
    executor.submit(
        submit_claim,
        TOKEN_STUDENT_2,
        "Student 2"
    )
]

    for future in futures:
        student, status, result = future.result()
        print(f"\n{student} | HTTP {status}")
        print(result)

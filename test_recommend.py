import requests

url = "http://localhost:8000/api/candidates/1" # Assuming candidate 1 exists
payload = {
    "stage": "用人部门筛选",
    "operator": "HR Manager (推至: 研发总监 (Manager_Tech), 评语: 这是一段很长很长的评语这可能超过了100个字符的限制这是一段很长很长的评语这可能超过了100个字符的限制这是一段很长很长的评语这可能超过了100个字符的限制)"
}
response = requests.patch(url, json=payload)
print(response.status_code)
print(response.text)

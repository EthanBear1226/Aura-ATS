import requests

with open('dummy.pdf', 'rb') as f:
    files = {'file': ('dummy.pdf', f, 'application/pdf')}
    data = {'job_title': '默认（AI自动提取）', 'operator': '系统'}
    response = requests.post('http://127.0.0.1:8000/api/parse-resume', files=files, data=data)
    print(response.status_code)
    print(response.json())

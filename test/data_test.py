import json
a = json.load(open('data/test_server_data/server_data.json', 'r', encoding='utf-8'))
print(a[0].keys())
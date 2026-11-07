#!/usr/bin/env python3
"""Gọi REST API của Cube (dev mode, không cần token).  python cube/query.py '{"measures":["orders.count"]}'"""
import json, sys, urllib.request, urllib.parse
q = json.loads(sys.argv[1])
url = "http://localhost:4000/cubejs-api/v1/load?query=" + urllib.parse.quote(json.dumps(q))
for _ in range(20):
    with urllib.request.urlopen(urllib.request.Request(url)) as r:
        body = json.loads(r.read())
    if body.get("error") == "Continue wait":
        import time; time.sleep(1); continue
    break
print(json.dumps(body.get("data", body), ensure_ascii=False)[:900])

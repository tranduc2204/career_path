"""API giả lập của Mây Shop (KHÔNG phải phần bạn cần sửa).

GET /v1/orders?updated_since=<ISO-8601>&page=<n>&page_size=<k>
    → {"data": [...], "page": n, "next_page": n+1 | null}
    Đơn có updated_at >= updated_since (bao gồm cả mốc), sắp theo (updated_at, order_id).
    updated_at có múi giờ +07:00. amount là CHUỖI kiểu Việt Nam: "1.290.000".
    Mỗi đơn có mảng lồng `items`.
GET /v1/customers?page=<n>&page_size=<k>   → như trên, không có updated_since

Trạng thái của API đổi theo "ngày" (api.set_day): ngày 1 có 6 đơn cũ đổi trạng thái + 8 đơn mới.
Bật api.flaky = True để mỗi endpoint trả 429 (Too Many Requests) ở lần gọi ĐẦU TIÊN.
Mọi request được ghi lại trong api.requests: list[(path, dict query)].
"""
import json
import random
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VN = timezone(timedelta(hours=7))


def vnd(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def build_data(seed: int = 11):
    rng = random.Random(seed)
    customers = [{"customer_id": i, "name": f"Khách {i:03d}", "city": rng.choice(["Ha Noi", "Ho Chi Minh", "Da Nang"])}
                 for i in range(1, 41)]
    base = datetime(2026, 12, 1, 8, 0, tzinfo=VN)
    day0 = []
    for i in range(1, 121):
        items = [{"sku": f"SKU{rng.randint(1, 30):02d}", "qty": rng.randint(1, 3),
                  "price": rng.choice([99_000, 149_000, 299_000, 1_290_000])} for _ in range(rng.randint(1, 3))]
        day0.append({
            "order_id": 5000 + i,
            "customer_id": rng.randint(1, 40),
            "status": "placed",
            "amount": sum(it["qty"] * it["price"] for it in items),
            "updated_at": base + timedelta(minutes=7 * i),
            "items": items,
        })
    # ngày 1: 6 đơn cũ đổi trạng thái (updated_at mới), 8 đơn mới
    day1 = [dict(o) for o in day0]
    t1 = datetime(2026, 12, 2, 9, 0, tzinfo=VN)
    for k, idx in enumerate([3, 10, 25, 50, 77, 119]):
        day1[idx] = {**day1[idx], "status": "shipped", "updated_at": t1 + timedelta(minutes=k)}
    for j in range(1, 9):
        items = [{"sku": "SKU07", "qty": 1, "price": 299_000}]
        day1.append({"order_id": 6000 + j, "customer_id": j, "status": "placed", "amount": 299_000,
                     "updated_at": t1 + timedelta(hours=1, minutes=j), "items": items})
    return customers, {0: day0, 1: day1}


class FakeApi:
    def __init__(self):
        self.customers, self.days = build_data()
        self.day = 0
        self.flaky = False
        self.requests: list[tuple[str, dict]] = []
        self._seen_429: set[str] = set()
        self._server = None
        self._thread = None
        self.base_url = None

    # ------------------------------------------------------------------ điều khiển
    def set_day(self, day: int):
        self.day = day

    def start(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                u = urlparse(self.path)
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                api.requests.append((u.path, q))
                if api.flaky and u.path not in api._seen_429:
                    api._seen_429.add(u.path)
                    self.send_response(429)
                    self.send_header("Retry-After", "0")
                    self.end_headers()
                    return
                status, body = api.handle(u.path, q)
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    # ------------------------------------------------------------------ logic API
    def handle(self, path, q):
        page = int(q.get("page", 1))
        size = min(int(q.get("page_size", 50)), 100)
        if path == "/v1/orders":
            rows = sorted(self.days[self.day], key=lambda o: (o["updated_at"], o["order_id"]))
            if "updated_since" in q:
                since = datetime.fromisoformat(q["updated_since"])
                if since.tzinfo is None:
                    return 400, {"error": "updated_since phải có múi giờ"}
                rows = [o for o in rows if o["updated_at"] >= since]
            rows = [{**o, "amount": vnd(o["amount"]), "updated_at": o["updated_at"].isoformat()} for o in rows]
        elif path == "/v1/customers":
            rows = self.customers
        else:
            return 404, {"error": "not found"}
        chunk = rows[(page - 1) * size: page * size]
        has_next = page * size < len(rows)
        return 200, {"data": chunk, "page": page, "next_page": page + 1 if has_next else None}


if __name__ == "__main__":
    import time
    api = FakeApi().start()
    print("API giả lập chạy ở", api.base_url, "(Ctrl+C để dừng)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        api.stop()

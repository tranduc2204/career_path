#!/usr/bin/env python3
"""Rút một đề system design ngẫu nhiên và chạy đồng hồ theo 6 bước của khung trả lời (16.0).

  python tools/drill.py              # đề ngẫu nhiên, 45 phút
  python tools/drill.py --minutes 60 # đổi tổng thời gian (các bước co giãn theo tỉ lệ)
  python tools/drill.py --list       # xem danh sách đề
  python tools/drill.py --pick D3    # chọn đề cụ thể
  python tools/drill.py --no-timer   # chỉ in đề

Chỉ dùng thư viện chuẩn. Ctrl+C để dừng giữa chừng.
"""
import argparse
import random
import sys
import time

PROMPTS = {
    "1": "Thiết kế tầng transformation cho ngân hàng: core banking (CDC), thẻ (file), cho vay (CDC), CRM (API). Báo cáo quản trị, báo cáo cơ quan quản lý, phân tích khách hàng.",
    "2": "500 model dbt, 4 đội, 30 nguồn. Người dùng phát hiện sai số trước đội dữ liệu 2 lần/tuần, mỗi sáng hàng chục cảnh báo không ai đọc. Thiết kế data quality framework.",
    "3": "dbt project 300 model trên Snowflake, 12 người commit, mọi người chạy prod từ máy cá nhân, vừa có sự cố xoá cột làm gãy 3 dashboard. Thiết kế CI/CD và môi trường.",
    "4": "150 stored procedure SQL Server sinh báo cáo kế toán/kho/bán hàng, không test, người viết đã nghỉ. Chuyển sang dbt trên cloud warehouse trong 6 tháng.",
    "5": "6 đội domain tự định nghĩa metric, BGĐ thấy 3 con số 'doanh thu' mỗi cuộc họp. Metric tập trung hay theo domain?",
    "6": "1 dbt project 1.200 model, 25 người, 5 đội, CI 35 phút, đội này làm hỏng model đội kia. Có nên tách project? Mono-repo hay multi-repo?",
    "7": "BGĐ muốn hỏi trợ lý AI về số liệu. Bản thử LLM tự viết SQL sai 40%. Thiết kế hệ thống để câu trả lời đáng tin.",
    "8": "Flash sale: vận hành muốn xem doanh thu, số đơn, tỉ lệ thanh toán lỗi theo phút. Hiện dbt chạy mỗi giờ trên BigQuery.",
    "D1": "Customer 360 cho chuỗi bán lẻ omnichannel (web, app, 300 cửa hàng, CRM, loyalty).",
    "D2": "Hệ thống tính hoa hồng cho đội sale: bậc doanh số, chính sách đổi theo quý, hoàn đơn sau chi trả.",
    "D3": "Báo cáo marketing đa kênh (Google, Meta, TikTok) và attribution.",
    "D4": "Kho dữ liệu cho SaaS B2B: subscription, MRR, churn, NRR.",
    "D5": "Chi phí warehouse tăng 30%/tháng. Thiết kế chương trình tối ưu chi phí.",
    "D6": "Nền tảng dữ liệu cho chuỗi phòng khám (dữ liệu sức khoẻ nhạy cảm).",
    "D7": "Data contract giữa đội app và đội dữ liệu cho event tracking.",
    "D8": "Chuyển 200 model dbt từ Redshift sang Snowflake/BigQuery.",
    "D9": "Báo cáo tồn kho đa kho, nhiều đơn vị tính, kiểm kê điều chỉnh lùi ngày.",
    "D10": "Self-serve analytics cho 300 nhân viên không biết SQL.",
    "D11": "Bảng đặc trưng (feature) cho đội ML, đúng tại thời điểm dự đoán.",
    "D12": "Báo cáo hợp nhất cho công ty mẹ có 5 công ty con dùng ERP khác nhau.",
    "D13": "Thiết kế lại dbt project 900 model, không chuẩn tên, 40% không ai dùng.",
    "D14": "Lineage và phân tích tác động thay đổi xuyên công cụ: nguồn → dbt → BI.",
}

STEPS = [  # (tên, tỉ lệ thời gian, nhắc)
    ("1. LÀM RÕ", 0.15, "người dùng · nguồn · độ tươi/độ đúng · ràng buộc · đội → CHỐT GIẢ ĐỊNH"),
    ("2. ƯỚC LƯỢNG", 0.07, "dòng/ngày, dòng/năm, snapshot, cửa sổ chạy → quyết định gì?"),
    ("3. KIẾN TRÚC", 0.18, "sơ đồ trái → phải, mũi tên có nhãn, mỗi tầng 1 câu vì sao"),
    ("4. ĐI SÂU", 0.38, "2–3 chỗ khó: grain/khoá, late data, đối soát... mỗi chỗ 2 phương án → chọn"),
    ("5. VẬN HÀNH", 0.16, "DQ · SLA · CI/CD · sự cố · bảo mật · chi phí"),
    ("6. TỔNG KẾT", 0.06, "3 quyết định chính · rủi ro lớn nhất · v2/v3"),
]


def fmt(sec):
    return f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=45)
    ap.add_argument("--pick")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-timer", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, v in PROMPTS.items():
            print(f"{k:>4}  {v}")
        return
    key = a.pick.upper() if a.pick else random.choice(list(PROMPTS))
    if key not in PROMPTS:
        sys.exit(f"Không có đề {key}. Xem --list")
    print("=" * 78)
    print(f"ĐỀ {key}: {PROMPTS[key]}")
    print("=" * 78)
    if a.no_timer:
        return
    total = a.minutes * 60
    input(f"\nTổng {a.minutes} phút. Bật ghi âm, Enter để bắt đầu...")
    t0 = time.time()
    try:
        for name, ratio, hint in STEPS:
            dur = total * ratio
            end = time.time() + dur
            print(f"\n▶ {name} ({fmt(dur)}) — {hint}")
            while (left := end - time.time()) > 0:
                print(f"\r   còn {fmt(left)} · đã {fmt(time.time() - t0)}   ", end="", flush=True)
                time.sleep(1)
            print("\a\r   ⏰ hết giờ bước này" + " " * 20)
    except KeyboardInterrupt:
        print("\nDừng.")
    print(f"\nXong sau {fmt(time.time() - t0)}. Chấm bằng tuan-16-system-design/12-phieu-tu-cham.md")


if __name__ == "__main__":
    main()

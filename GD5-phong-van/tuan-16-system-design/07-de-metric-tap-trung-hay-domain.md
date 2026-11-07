# 16.7 Đề 5 (Senior): Metric tập trung hay theo domain?

> Nền: [GĐ3 tuần 8](../../GD3-ly-thuyet/README.md) (semantic layer). Đây là câu **thảo luận kiến trúc + tổ chức**, thường 15–25 phút, không vẽ chi tiết như đề 1.

## Đề

> *"Công ty có 6 đội dữ liệu theo domain (sales, marketing, finance, product, ops, risk). Mỗi đội tự định nghĩa metric. Ban giám đốc phàn nàn mỗi cuộc họp có 3 con số 'doanh thu'. Một số người muốn một đội metric trung tâm định nghĩa mọi thứ, số khác muốn các domain tự chủ. Bạn đề xuất gì?"*

## Làm rõ nhanh

- Những metric nào đang lệch? Thường **ít** (doanh thu, khách hoạt động, CAC), không phải mọi metric.
- Ai dùng chúng: BGĐ, nhà đầu tư, báo cáo tài chính, hay nội bộ đội?
- Semantic layer đã có chưa, BI là gì, dbt một project hay Mesh?

## Hai cực và điểm giữa

| | Tập trung hoàn toàn | Domain tự chủ hoàn toàn | **Liên bang (federated)**: đề xuất |
|---|---|---|---|
| Ai định nghĩa | Đội metric trung tâm | Mỗi đội | **Metric cấp công ty**: có chủ + hội đồng duyệt. **Metric domain**: đội tự định nghĩa |
| Nhất quán | Cao | Thấp | Cao ở chỗ cần (KPI công ty), linh hoạt ở chỗ khác |
| Tốc độ | Chậm, đội trung tâm thành nút cổ chai | Nhanh | Nhanh cho domain, có quy trình cho KPI |
| Hiểu nghiệp vụ | Thấp hơn (đội trung tâm xa nghiệp vụ) | Cao | Chủ metric là domain hiểu nó nhất |
| Hợp | Công ty nhỏ, 1 đội dữ liệu | Startup giai đoạn đầu, chưa có KPI chung | Công ty nhiều đội (bối cảnh này) |

## Thiết kế mô hình liên bang

```
TẦNG METRIC CÔNG TY (certified)              TẦNG METRIC DOMAIN
  revenue, gross_margin, active_customers      marketing: cac, roas, mql_to_sql
  nps, nrr ...                                 product: dau, feature_adoption
  ─ mỗi metric có 1 domain chủ (vd revenue      risk: npl_ratio ...
    → finance), định nghĩa viết ra chữ          ─ đội tự tạo, tự review
  ─ thay đổi cần duyệt (finance + data lead)    ─ được dùng metric công ty làm input
  ─ tag "certified" trên semantic layer + BI    ─ KHÔNG được tạo metric trùng tên/ý nghĩa
  ─ có test đối chiếu số neo (kỳ đã khoá)          với metric công ty
                         │                              │
                         └──── cùng một semantic layer (MetricFlow / Cube / LookML) ────┘
                                    trên các mart public có contract
```

Cơ chế cụ thể:

1. **Danh mục metric** (metric catalog): tên, định nghĩa bằng lời, công thức, chủ, cấp (company/domain), trạng thái (draft/certified/deprecated). Sinh tự động từ YAML semantic layer, hiện trong catalog/BI.
2. **Quy trình certified:** PR thay đổi metric công ty cần CODEOWNERS của domain chủ + data lead; CI chạy test số neo (doanh thu tháng đã khoá không đổi); thông báo thay đổi cho người dùng.
3. **Chống trùng:** lint trong CI: metric mới không được trùng tên, cảnh báo nếu công thức gần giống metric certified.
4. **Hiển thị trong BI:** metric certified có huy hiệu; dashboard BGĐ chỉ được dùng metric certified.
5. **Khi định nghĩa thật sự khác nhau** (doanh thu kế toán vs doanh thu bán hàng): đó là **hai metric khác tên** (`revenue_recognized`, `bookings`), không phải một metric hai phiên bản.

## Kỹ thuật: ở dbt Mesh / semantic layer

- Một project "metrics" (hoặc mỗi domain project sở hữu metric của mình) dựa trên **model public** của các domain.
- MetricFlow: metric đặt cạnh semantic model của domain chủ; `config: meta: {tier: certified, owner: ...}`; group của metric = domain chủ.
- Câu hỏi khó: metric công ty cần dữ liệu của nhiều domain (CAC = chi phí marketing / khách mới của sales). Chủ là ai? → chọn **một** domain chủ (marketing), các domain kia cung cấp model public có contract.

## Đo thành công

- Số metric "trùng nghĩa khác số" phát hiện trong họp → 0 với KPI công ty.
- % dashboard BGĐ chỉ dùng metric certified.
- Thời gian đưa một metric domain mới vào dùng (không được chậm đi).

## Câu hỏi đào sâu

1. **"Đội trung tâm có cần không?"** → Cần một **đội nền tảng** nhỏ giữ công cụ, quy trình, chuẩn và hội đồng duyệt. Không định nghĩa thay domain.
2. **"Một domain sửa model public làm metric công ty thay đổi?"** → Contract + version cho model public; CI của domain chạy test số neo của metric certified phụ thuộc vào model đó.
3. **"AI agent dùng metric nào?"** → Chỉ metric certified và metric domain đã duyệt có mô tả tốt. Đây là lý do metadata (description, synonyms) quan trọng (đề 7).

## Câu trả lời 2 phút (để luyện nói)

> *"Em đề xuất mô hình liên bang. Chỉ một số ít KPI công ty, khoảng 10–20 cái như doanh thu, biên lợi nhuận, khách hoạt động, là 'certified': mỗi cái có một domain chủ, định nghĩa viết rõ, thay đổi phải qua duyệt và có test số neo. Còn lại các domain tự định nghĩa metric của mình trên cùng một semantic layer, chỉ cấm trùng nghĩa với metric certified. Như vậy BGĐ có một con số doanh thu, còn các đội không bị một đội trung tâm làm chậm. Khi hai định nghĩa thật sự khác nhau, ví dụ doanh thu ghi nhận theo kế toán và doanh thu bán hàng, em đặt hai tên khác nhau thay vì tranh cãi một tên."*

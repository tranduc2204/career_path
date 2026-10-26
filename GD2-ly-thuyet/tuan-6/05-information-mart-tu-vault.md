# 6.5 Information mart: dựng star schema từ vault

## Vì sao vẫn cần Kimball

Người dùng BI không thể (và không nên) join hub + link + 6 satellite + lọc phiên bản. Data Vault là **tầng tích hợp và lưu trữ**; tầng **hiển thị** vẫn là star schema (hoặc bảng phẳng). Câu cửa miệng: *"Data Vault không thay Kimball, nó nằm phía dưới Kimball."*

```
raw vault ─▶ business vault ─▶ information mart (dim_*, fct_*) ─▶ BI / semantic layer
```

Bài V8 của lab chứng minh điều này: `dim_customer_dv` và `fct_sales_dv` dựng từ vault ra **giống hệt từng dòng** bản Kimball của tuần 4.

## Dựng dimension từ vault

### Dimension SCD2 theo thời gian nghiệp vụ

```sql
with status as (                                  -- 1 dòng satellite = 1 phiên bản
    select h.customer_code, s.city, s.loyalty_tier, s.EFFECTIVE_FROM,
           row_number() over (partition by s.CUSTOMER_HK order by s.EFFECTIVE_FROM) as version_seq
    from {{ ref('sat_customer_crm_status') }} s
    join {{ ref('hub_customer') }} h using (CUSTOMER_HK)
),
versions as (
    select customer_code, city, loyalty_tier,
           case when version_seq = 1 then timestamp '1900-01-01' else EFFECTIVE_FROM end as valid_from
    from status
)
select *, coalesce(lead(valid_from) over (partition by customer_code order by valid_from),
                   timestamp '9999-12-31') as valid_to
from versions
```

| Thành phần dimension | Lấy từ vault |
|---|---|
| Danh sách thực thể | **hub** (mọi key, mọi nguồn) |
| Thuộc tính Type 2 | các dòng **satellite**, khoảng hiệu lực từ `EFFECTIVE_FROM` (thời gian nghiệp vụ) |
| Thuộc tính Type 1 | dòng **mới nhất** của satellite (`qualify row_number() over (... order by LOAD_DATETIME desc) = 1`) |
| Inferred member | key có trong hub mà satellite chưa có dòng nào |
| Unknown / not applicable | zero key (`-1`, `-2`) của hub → thành viên `-1`, `-2` của dimension |
| Gộp nhiều nguồn | nhiều satellite (hoặc computed satellite ở business vault) + PIT |

Dimension dạng "trạng thái tại mỗi mốc" (snapshot dimension) thì đọc qua **PIT** (6.4), chỉ equi-join.

### Load date hay effective date?

| Câu hỏi | Dùng |
|---|---|
| "Khách ở thành phố nào **lúc mua**?" (báo cáo doanh thu) | `EFFECTIVE_FROM` (thời gian nghiệp vụ) |
| "Kho **biết** khách ở đâu vào lúc báo cáo tháng 3 được gửi?" (kiểm toán) | `LOAD_DATETIME` (qua PIT) |

Dùng `LOAD_DATETIME` cho `valid_from` của dimension nghiệp vụ → hoá đơn trễ (HN-0003) bị gắn phiên bản sai, mọi phiên bản lệch 1 ngày.

## Dựng fact từ vault

| Thành phần fact | Lấy từ vault |
|---|---|
| Grain | **link** hoặc **non-historized link** (dòng đơn = `nh_link_order_line`) |
| Measure bất biến | payload của non-historized link |
| Thuộc tính đầu đơn (trạng thái, ngày, phí ship) | dòng **mới nhất** của satellite của hub/link (`sat_order_shop`, `sat_order_pos`) |
| Khoá dimension | đi qua link tới hub (`link_order_customer → hub_customer`), rồi tra dimension theo thời điểm |
| Khoá surrogate | **cùng công thức** với dimension (`generate_surrogate_key`) để join được |

```sql
shop_header as (
    select ORDER_HK, channel, payment_method, is_gift, shipping_fee, order_status, order_ts
    from {{ ref('sat_order_shop') }}
    qualify row_number() over (partition by ORDER_HK order by LOAD_DATETIME desc) = 1
)
```

Đếm số join: `fct_sales_dv` của lab đọc 9 bảng (2 non-historized link, 3 hub, 2 satellite đầu đơn, link khách, dimension) trong khi bản Kimball đọc 4 bảng staging rồi tra 4 dimension. Đó là lý do mart từ vault thường được **materialize thành table**.

## View hay table?

| Cách | Khi nào |
|---|---|
| **View** (virtual mart) | Vault nhỏ/vừa, có PIT/bridge hỗ trợ, cần dữ liệu luôn mới nhất, muốn đổi logic mart không phải chạy lại |
| **Table** | Mart lớn, BI truy vấn nhiều, join phức tạp. Phổ biến nhất trong dbt |
| **Incremental** | Fact rất lớn. Lưu ý: vault insert-only nên dễ lọc theo `LOAD_DATETIME` của link/satellite |

Nhiều tài liệu Data Vault đề cao mart **ảo hoá** (virtualization): vì mọi thứ dựng lại được từ vault, mart chỉ là view. Trong thực tế với dbt, `table` cho mart lớn + `view` cho mart nhỏ là cân bằng tốt.

## Kiểm thử information mart

| Test | Cách |
|---|---|
| Đối soát với nguồn | `sum(net_amount)` theo đơn = `total_amount` của nguồn (giống K5) |
| Đối soát với bản cũ | Khi chuyển từ Kimball sang vault: `except` hai chiều phải rỗng (lab V8). Dùng `audit_helper.compare_relations` trên Snowflake |
| Cấu trúc | Contract (GĐ1, 3.4) trên mart public để đổi tầng dưới không phá BI |

Mẹo chuyển đổi an toàn: giữ nguyên **tên và contract** của mart cũ, thay phần thân bằng SQL đọc từ vault, chạy đối soát `except` trong CI cho tới khi bằng 0.

## Lỗi hay gặp

- Dùng `LOAD_DATETIME` làm thời gian hiệu lực của dimension nghiệp vụ.
- Lấy "dòng mới nhất" của satellite bằng `max(LOAD_DATETIME)` rồi join lại → chậm, dễ trùng; dùng `qualify row_number()`.
- Quên zero key `-2` → khách vãng lai thành inferred member.
- Công thức surrogate key ở fact khác ở dimension → join không khớp.
- Để BI query thẳng raw vault.

## Áp dụng vào adventure_works

- [ ] Dựng lại `dim_customer` hoặc `dim_product` từ vault, so `except` với bản Kimball hiện có, đưa kết quả vào ADR
- [ ] Dựng `fct_sales_dv` từ `nh_link` dòng đơn, so tổng doanh thu với `fct_sales`
- [ ] Giữ contract của mart cũ; nếu chuyển hẳn sang vault, chỉ đổi phần thân model

## Câu hỏi tự kiểm tra

1. Vì sao nói Data Vault "nằm phía dưới" Kimball?
2. Dimension SCD2 lấy danh sách thực thể, thuộc tính Type 1, Type 2, inferred member từ đâu trong vault?
3. Khi nào dùng `EFFECTIVE_FROM`, khi nào `LOAD_DATETIME`?
4. Fact dòng đơn lấy grain từ bảng nào của vault?
5. Mart từ vault nên là view hay table?
6. Làm sao chứng minh mart dựng từ vault đúng bằng mart cũ?

## Tài liệu

- *Building a Scalable Data Warehouse with Data Vault 2.0* — chương 7 (Dimensional modeling), chương 14 (Loading the dimensional information mart)
- dbt package `audit_helper` (so sánh 2 bảng): https://hub.getdbt.com/dbt-labs/audit_helper/latest/
- Lab: [V8](../../bai-tap-kimball-data-vault/bai-tap/05-data-vault-business-vault-va-mart.md)

# 6.4 Business vault: computed satellite, PIT, bridge

## Business vault là gì

Raw vault giữ dữ liệu **thô**, đúng như nguồn gửi. Business vault là tầng **mở rộng** raw vault bằng:

1. **Quy tắc nghiệp vụ** (soft rules): dữ liệu được tính toán, hợp nhất, làm sạch theo nghĩa nghiệp vụ.
2. **Bảng hỗ trợ truy vấn** (query assistance): PIT, bridge — chỉ để truy vấn nhanh và dễ hơn.

Business vault dùng **cùng loại cấu trúc** (hub, link, satellite) và vẫn insert-only, nhưng mọi bảng ở đây đều **tính ra được từ raw vault** → xoá đi dựng lại được.

```
RAW VAULT (không đụng tới)              BUSINESS VAULT (tính từ raw vault)
hub_customer ───────────────────────┬── bsat_customer_value   (computed satellite: tổng chi tiêu, hạng A/B/C)
sat_customer_crm_status ────────────┤
sat_customer_crm_profile ───────────┼── pit_customer          (con trỏ theo mốc thời gian)
link_product_category + eff_sat ────┴── bridge_product_category (đường đi qua link theo mốc thời gian)
```

## Computed satellite (business satellite)

Satellite chứa **thuộc tính được tính** từ dữ liệu raw vault theo quy tắc nghiệp vụ:

| Ví dụ | Quy tắc |
|---|---|
| `bsat_customer_golden` | Gộp tên/email/thành phố từ CRM, shop, sàn TMĐT theo thứ tự ưu tiên nguồn ("CRM thắng") |
| `bsat_customer_value` | Tổng chi tiêu 12 tháng, hạng A/B/C |
| `bsat_order_status` | Trạng thái đơn hợp nhất từ shop + kho vận |

Vì sao không tính thẳng vào raw vault: quy tắc đổi thì chỉ **tính lại** business vault; raw vault (bằng chứng gốc) không bị đụng. Kiểm toán vẫn so được "nguồn nói gì" và "quy tắc kết luận gì".

## PIT (Point-In-Time) table

### Vấn đề

Muốn "trạng thái của khách tại thời điểm T" từ 2 satellite, mỗi satellite phải tìm dòng **hiệu lực tại T** bằng join theo khoảng:

```sql
-- không có PIT: mỗi satellite một join theo khoảng, phải tự tính end date bằng lead()
from hub_customer h
left join (select *, lead(LOAD_DATETIME) over (partition by CUSTOMER_HK order by LOAD_DATETIME) as next_ldts
           from sat_customer_crm_status) s
  on s.CUSTOMER_HK = h.CUSTOMER_HK and s.LOAD_DATETIME <= :T and (s.next_ldts > :T or s.next_ldts is null)
left join (...tương tự cho sat_customer_crm_profile...)
```

Với 6 satellite và 365 mốc, câu này vừa khó viết vừa rất chậm.

### Cấu trúc PIT

PIT **tính sẵn** con trỏ cho mỗi (key × mốc):

| CUSTOMER_HK | AS_OF_DATE | sat_customer_crm_status_PK | sat_customer_crm_status_LDTS | sat_customer_crm_profile_PK | sat_customer_crm_profile_LDTS |
|---|---|---|---|---|---|
| hash(C005) | 2026-03-04 06:00 | hash(C005) | 2026-03-02 06:00 | hash(C005) | 2026-03-02 06:00 |
| hash(C005) | 2026-03-05 06:00 | hash(C005) | 2026-03-05 06:00 | hash(C005) | 2026-03-02 06:00 |
| hash(C013) | 2026-03-02 06:00 | 000…0 (ghost) | 1900-01-01 | 000…0 (ghost) | 1900-01-01 |

Truy vấn sau đó chỉ còn **equi-join**:

```sql
from {{ ref('pit_customer') }} p
join {{ ref('hub_customer') }} h on h.CUSTOMER_HK = p.CUSTOMER_HK
left join {{ ref('sat_customer_crm_status') }} st
       on st.CUSTOMER_HK = p.sat_customer_crm_status_PK
      and st.LOAD_DATETIME = p.sat_customer_crm_status_LDTS
```

Chưa có dòng satellite tại mốc đó → con trỏ trỏ vào **ghost record** (hash toàn 0, ngày 1900), join trả về null mà không rơi dòng.

### Bảng as-of-dates

PIT tính theo một bảng các mốc thời gian. Thiết kế mốc là quyết định quan trọng:

| Mốc | Trả lời |
|---|---|
| Mỗi lần nạp (lab V7) | "Sau lần nạp X, kho biết gì?" (kiểm toán) |
| Cuối mỗi ngày nghiệp vụ | Snapshot hằng ngày cho báo cáo |
| Cuối tháng | Báo cáo tháng, giảm kích thước |
| **Logarit**: hằng ngày cho 30 ngày gần nhất, hằng tháng cho cũ hơn | Cân bằng chi tiết và dung lượng |

Kích thước PIT = số key × số mốc. 1 triệu khách × 365 mốc = 365 triệu dòng/năm → mốc phải chọn có chủ đích, PIT cũ có thể xoá bớt (vì dựng lại được).

### PIT dùng LOAD_DATETIME

automate_dv tính PIT theo `LOAD_DATETIME` (lúc kho biết). Muốn trạng thái theo **thời gian nghiệp vụ** (khách ở đâu lúc mua hàng), mart thường dùng `EFFECTIVE_FROM` của satellite (lab V8) thay vì PIT.

## Bridge (của Data Vault)

⚠️ **Trùng tên với bridge của Kimball (4.4) nhưng khác nghĩa.**

| | Bridge Kimball | Bridge Data Vault |
|---|---|---|
| Để làm gì | Dimension nhiều giá trị / phân cấp không đều | **Đường tắt** đi qua chuỗi hub – link – hub, theo mốc thời gian |
| Chứa | group key, khoá dimension, trọng số | hash key của hub gốc, các link trên đường đi, `AS_OF_DATE` |

Ví dụ: "tại mốc T, sản phẩm thuộc danh mục nào" phải đi `hub_product → link_product_category → hub_category`, lọc theo effectivity satellite. Bridge lưu sẵn kết quả của đường đi đó cho từng mốc, giống PIT nhưng cho **quan hệ** thay vì thuộc tính.

```sql
{{ config(materialized='bridge_incremental') }}
{{ automate_dv.bridge(source_model='hub_product', src_pk='PRODUCT_HK', src_ldts='LOAD_DATETIME',
                      as_of_dates_table='as_of_date',
                      bridge_walk={
                          'PRODUCT_CATEGORY': {
                              'bridge_link_pk': 'LINK_PRODUCT_CATEGORY_HK',
                              'bridge_end_date': 'EFF_SAT_PRODUCT_CATEGORY_ENDDATE',
                              'bridge_load_date': 'EFF_SAT_PRODUCT_CATEGORY_LOADDATE',
                              'link_table': 'link_product_category',
                              'link_pk': 'LINK_PRODUCT_CATEGORY_HK',
                              'link_fk1': 'PRODUCT_HK', 'link_fk2': 'CATEGORY_HK',
                              'eff_sat_table': 'eff_sat_product_category',
                              'eff_sat_pk': 'LINK_PRODUCT_CATEGORY_HK',
                              'eff_sat_end_date': 'END_DATE', 'eff_sat_load_date': 'LOAD_DATETIME'}},
                      stage_tables_ldts={'v_stg_erp__products': 'LOAD_DATETIME'}) }}
```

(Thử thách C9 của lab.)

## PIT và bridge là "bảng phái sinh"

- Không chứa dữ liệu mới, chỉ chứa **con trỏ** → xoá đi dựng lại được.
- Không cần giữ mãi: có thể chỉ giữ mốc gần đây.
- Lý do tồn tại duy nhất là **hiệu năng và sự đơn giản** cho tầng mart. Nếu mart nhỏ, query trực tiếp vault vẫn đủ nhanh, có thể không cần PIT.

## Lỗi hay gặp

- Đặt quy tắc nghiệp vụ vào raw vault → quy tắc đổi phải sửa dữ liệu gốc.
- PIT với mốc hằng ngày cho cả 10 năm → bảng khổng lồ.
- Nhầm bridge Kimball với bridge Data Vault khi đọc tài liệu.
- Dùng PIT (theo `LOAD_DATETIME`) cho báo cáo cần thời gian nghiệp vụ → lệch 1 ngày.
- Quên rằng PIT trỏ vào ghost record → `inner join` satellite làm rơi dòng.

## Áp dụng vào adventure_works

- [ ] `as_of_date` theo tháng (dữ liệu AdventureWorks trải nhiều năm)
- [ ] `pit_person` trên 2 satellite của `Person` (tên tách PII + thông tin khác)
- [ ] 1 computed satellite: `bsat_customer_value` (tổng `TotalDue` theo khách)
- [ ] Ghi vào README: bảng nào là raw vault, bảng nào là business vault, bảng nào dựng lại được

## Câu hỏi tự kiểm tra

1. Business vault khác raw vault ở điểm nào? Vì sao không tính quy tắc nghiệp vụ thẳng vào raw vault?
2. PIT giải quyết vấn đề gì? Mô tả cấu trúc một dòng PIT.
3. Ghost record trong PIT để làm gì?
4. Chọn mốc as-of thế nào? Mốc "logarit" là gì?
5. Bridge Data Vault khác bridge Kimball thế nào?
6. Vì sao PIT và bridge xoá đi dựng lại được?

## Tài liệu

- *Building a Scalable Data Warehouse with Data Vault 2.0* — chương 2 (kiến trúc: raw vault, business vault), chương 6 (Advanced Data Vault modeling: PIT, bridge)
- AutomateDV — PIT và bridge: https://automate-dv.readthedocs.io/en/latest/
- Lab: [V7](../../bai-tap-kimball-data-vault/bai-tap/05-data-vault-business-vault-va-mart.md)

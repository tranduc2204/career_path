# 6.2 Hub, link, satellite chi tiết

## Hash key: nền móng của Data Vault 2.0

DV 1.0 dùng sequence key (số tự tăng). DV 2.0 dùng **hash của business key**.

| | Sequence key | Hash key |
|---|---|---|
| Tính khi nào | Lúc insert vào hub (phải tra hub) | Ở **staging**, chỉ từ dữ liệu nguồn |
| Nạp song song | Link/satellite phải đợi hub xong | Hub, link, satellite nạp **cùng lúc** |
| Giữa các môi trường | Khác nhau (dev ≠ prod) | Giống hệt |
| Nhược | | Dài hơn (16 byte MD5, 20 byte SHA-1), rủi ro trùng (collision) cực nhỏ |

### Chuẩn hoá trước khi băm

Hash của `' c003'` khác hash của `'C003'`. Mọi nơi phải băm **cùng một chuỗi chuẩn**:

```
1 cột:      UPPER(TRIM(CAST(cột AS VARCHAR)))               rỗng → NULL
nhiều cột:  'BK1' || '||' || 'BK2'     (dấu phân cách cố định)
            NULL trong tổ hợp → thay bằng '^^' (placeholder) để (A, NULL) khác (NULL, A)
```

automate_dv làm việc này (biến `concat_string = '||'`, `null_placeholder_string = '^^'`, `hash_content_casing = 'upper'`). Bạn chỉ cần business key đã được chuẩn hoá ở staging (hard rule).

MD5 vs SHA: MD5 đủ cho định danh (không dùng cho bảo mật), nhanh, 16 byte. SHA-1/SHA-256 giảm rủi ro trùng hơn nữa, tốn chỗ hơn. Chọn **một** và dùng thống nhất toàn kho (biến `hash` của automate_dv).

## Hub

**Hub = danh sách business key duy nhất của một khái niệm kinh doanh.**

| Cột | |
|---|---|
| `CUSTOMER_HK` | hash key (khoá chính) |
| `customer_code` | business key |
| `LOAD_DATETIME` | lần **đầu tiên** kho thấy key này, ở bất kỳ nguồn nào |
| `RECORD_SOURCE` | nguồn của lần thấy đầu tiên đó |

Chọn business key:
- Là định danh **người dùng nghiệp vụ** biết và dùng (mã khách, số đơn, SKU), không phải id tự tăng nội bộ của một phần mềm nếu tránh được.
- Hai nguồn dùng **cùng mã cho hai thứ khác nhau** (mã khách `123` ở CRM và `123` ở POS là 2 người) → thêm tiền tố nguồn/công ty vào business key (`CRM|123`), hoặc làm hub riêng.
- Một thực thể có **nhiều mã ở nhiều nguồn** (`C013` ở CRM, `TIKI_8812` ở sàn TMĐT) → giữ cả hai trong hub, nối bằng **same-as link**.
- Business key nhiều cột (composite): băm tổ hợp.

## Link

**Link = quan hệ giữa 2+ hub.** Luôn mô hình như **nhiều-nhiều**, kể cả khi nghiệp vụ hiện là một-nhiều: nghiệp vụ đổi (1 đơn nhiều khách?) thì không phải sửa cấu trúc.

| Cột | |
|---|---|
| `LINK_ORDER_CUSTOMER_HK` | hash của **tổ hợp** business key (`order_number || customer_code`) |
| `ORDER_HK`, `CUSTOMER_HK` | hash key của từng hub |
| `LOAD_DATETIME`, `RECORD_SOURCE` | lần đầu thấy quan hệ |

Link **không bao giờ bị sửa**: quan hệ cũ vẫn nằm đó khi quan hệ mới xuất hiện (SKU07–DT_PK và SKU07–TT_TUI cùng tồn tại). Muốn biết quan hệ nào đang hiệu lực → effectivity satellite.

### Các biến thể link

| Loại | Dùng khi | Ví dụ |
|---|---|---|
| **Standard link** | Quan hệ có thể kèm satellite mô tả | `link_order_customer` |
| **Non-historized link** (NH link, tên cũ: transactional link, t-link) | Giao dịch **bất biến**: không bao giờ sửa → payload để luôn trong link, không cần satellite | `nh_link_order_line` (số lượng, đơn giá), giao dịch ngân hàng |
| **Same-as link** (SAL) | Hai business key cùng chỉ một thực thể | `C013` ≡ `TIKI_8812` |
| **Hierarchical link** (HAL) | Quan hệ cha – con trong cùng một hub | danh mục ↔ danh mục cha, nhân viên ↔ quản lý |

**Dependent child key**: thành phần không phải business key nhưng cần để phân biệt dòng, như `line_no` của dòng đơn (cùng 1 sản phẩm có thể nằm ở 2 dòng). Đưa vào hash của link.

## Satellite

**Satellite = thuộc tính mô tả của hub hoặc link, theo thời gian.**

| Cột | |
|---|---|
| `CUSTOMER_HK` | khoá cha (hub hoặc link) |
| payload | `city`, `loyalty_tier`... |
| `CUSTOMER_STATUS_HASHDIFF` | hash của payload |
| `EFFECTIVE_FROM` | thời điểm nghiệp vụ (tuỳ chọn) |
| `LOAD_DATETIME`, `RECORD_SOURCE` | |

Khoá chính: `(CUSTOMER_HK, LOAD_DATETIME)`. **Test unique trên cặp này là test sức khoẻ quan trọng nhất của vault** (nó bắt được bẫy V4 của lab).

### Hashdiff: phát hiện thay đổi

Mỗi lần nạp, với mỗi key: so `HASHDIFF` của bản ghi mới với **dòng mới nhất** trong satellite. Khác → thêm dòng. Giống → bỏ qua. So 1 cột hash nhanh hơn so 20 cột payload, và xử lý được null.

Hệ quả cần nhớ:
- A → B → A tạo **3 dòng**: dòng thứ 3 so với dòng gần nhất (B), không so với mọi dòng cũ.
- Cột payload được **sắp xếp** trước khi băm, để đổi thứ tự cột trong code không sinh "thay đổi giả".
- Satellite **không có cột `end_date`** vật lý (insert-only). Khoảng hiệu lực tính bằng `lead(LOAD_DATETIME)` khi đọc, hoặc lưu sẵn trong PIT.

### Tách satellite theo tiêu chí nào

| Tiêu chí | Ví dụ |
|---|---|
| **Theo hệ thống nguồn** (luôn luôn) | `sat_customer_crm`, `sat_customer_shop`: mỗi nguồn 1 satellite, không trộn |
| **Theo tốc độ thay đổi** | `status` (hạng, thành phố: đổi thường) tách khỏi `profile` (tên: hiếm đổi) → satellite nhỏ, ít dòng thừa |
| **Theo độ nhạy / bảo mật** | Dữ liệu cá nhân (tên, email, CMND) để riêng → phân quyền, mã hoá, **xoá theo yêu cầu** dễ dàng |

### Các satellite đặc biệt

| Loại | Giải quyết | Ví dụ lab |
|---|---|---|
| **Effectivity satellite** | Link nào **đang** hiệu lực. Có **driving key**: phía quan hệ "dẫn dắt" (1 sản phẩm thuộc 1 danh mục tại 1 thời điểm → driving key = sản phẩm) | `eff_sat_product_category` (V5) |
| **Multi-active satellite** (MAS) | Một key có **nhiều** dòng hợp lệ cùng lúc. Thêm **child dependent key** để phân biệt | `ma_sat_customer_crm_phones` (nhiều số điện thoại, khoá con `phone_type`) (V6) |
| **Status tracking satellite** | Ghi nhận key **biến mất / xuất hiện lại** ở nguồn (xoá cứng) | Khách bị xoá khỏi file CRM |
| **Record tracking satellite** | Key xuất hiện trong lần nạp nào (theo dõi hoạt động) | |

Multi-active satellite ghi **cả tập** mỗi khi tập đổi: C001 chỉ đổi số di động nhưng số nhà riêng cũng được ghi lại với `LOAD_DATETIME` mới.

## Ghost record và zero key

| | Là gì | Dùng ở đâu |
|---|---|---|
| **Zero key** | Business key mặc định cho giá trị **thiếu** (`-1` bắt buộc mà thiếu, `-2` tuỳ chọn mà thiếu). Có dòng thật trong hub | Khách vãng lai → `customer_code = '-2'`, link luôn có hub để trỏ |
| **Ghost record** | Dòng **giả** trong satellite (hash toàn số 0, ngày 1900-01-01) | PIT trỏ vào ghost khi tại mốc đó chưa có dòng satellite → equi-join không rơi dòng |

Cùng ý tưởng với thành viên `-1` / `-2` của Kimball (4.3): không để khoá null.

## Load date vs effective date

| | `LOAD_DATETIME` | `EFFECTIVE_FROM` |
|---|---|---|
| Là | Lúc **kho nhận** bản ghi | Lúc thay đổi **có hiệu lực ngoài đời** |
| Lab, C003 chuyển nhà | 03/03 06:00 | 02/03 |
| Dùng cho | Kiểm toán ("kho biết lúc nào"), PIT, nạp incremental | Báo cáo nghiệp vụ, SCD2 trong information mart |

Data Vault **bắt buộc** có load date (nó là một phần của khoá satellite). Effective date là tuỳ chọn nhưng gần như luôn cần cho mart. Dùng nhầm → báo cáo lệch 1 ngày (lab V8, câu hỏi 2).

## Lỗi hay gặp

- Chọn id tự tăng của phần mềm nguồn làm business key → đổi phần mềm là mất định danh.
- Không chuẩn hoá business key trước khi băm → cùng khách 2 hash.
- Đặt thuộc tính vào hub, hoặc quan hệ vào satellite (danh mục của sản phẩm là **link**, không phải cột của satellite sản phẩm).
- Trộn nhiều nguồn vào 1 satellite.
- Satellite không có test unique `(HK, LOAD_DATETIME)`.
- Nghĩ rằng link cũ sẽ "tự biến mất" khi quan hệ đổi.

## Áp dụng vào adventure_works

Mô hình vault cho phần bán hàng (chuẩn bị cho [6.3](03-automate-dv.md)):

| Loại | Đề xuất | Nguồn |
|---|---|---|
| Hub | `hub_customer` (`CustomerID`... hoặc `AccountNumber` nếu muốn mã nghiệp vụ), `hub_person` (`BusinessEntityID`), `hub_product` (`ProductNumber`), `hub_sales_order` (`SalesOrderNumber`), `hub_store` | `Sales.Customer`, `Person.Person`, `Production.Product`, `Sales.SalesOrderHeader`, `Sales.Store` |
| Link | `link_customer_person`, `link_customer_store`, `link_order_customer`, `nh_link_order_line` (`SalesOrderDetail`), `link_product_subcategory` | |
| Satellite | `sat_person` (tên — tách PII), `sat_product`, `sat_sales_order_header` | |
| Multi-active | `ma_sat_person_phone` (`Person.PersonPhone`: 1 người nhiều số), email | |

- [ ] Vẽ sơ đồ hub–link–satellite trước khi code (draw.io / Mermaid trong README)
- [ ] Liệt kê business key của từng hub và lý do chọn

## Câu hỏi tự kiểm tra

1. Hash key hơn sequence key ở điểm nào? Mất gì?
2. Vì sao phải chuẩn hoá business key trước khi băm? automate_dv chuẩn hoá thế nào?
3. Vì sao link luôn là nhiều-nhiều?
4. Khi nào dùng non-historized link? Same-as link? Hierarchical link?
5. Hashdiff hoạt động thế nào? Vì sao A → B → A tạo 3 dòng?
6. Kể 3 tiêu chí tách satellite.
7. Effectivity satellite, multi-active satellite giải quyết gì? Driving key là gì?
8. Ghost record và zero key khác nhau thế nào?

## Tài liệu

- *Building a Scalable Data Warehouse with Data Vault 2.0* — chương 4 (Data Vault 2.0 modeling), chương 5 (Intermediate: satellites đặc biệt, link đặc biệt)
- AutomateDV docs (mục Tutorial mô tả từng loại bảng): https://automate-dv.readthedocs.io/en/latest/
- AutomateDV trên dbt Hub: https://hub.getdbt.com/Datavault-UK/automate_dv/latest/
- Lab: [V1–V6](../../bai-tap-kimball-data-vault/bai-tap/04-data-vault-raw-vault.md)

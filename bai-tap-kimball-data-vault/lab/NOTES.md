# stg_shop__orders
1. Nguồn nạp kiểu gì? Nguồn ghi đè mỗi ngày chạy (file full mỗi )
2. khóa chính là: order_number
3. 1 dòng = 1 order
4. measuare: shipping | total amount 
5. nối sang bảng customer thông qua cột customer_code, diménion: ngày kách sản phẩm địa điểm 

loại table fact: transaction 

------------------------------------------
quy trình:
gain:
dimension:
measure:
loại fact:
------------------------------------------


stg_shop__orders
quy trình: bán hàng (online + cửa hàng)
gain: 1 dòng là 1 đơn
dimension: ngày hóa đơn, khách.
measure: số lượng, đơn giá, giảm giá 
loại fact: transaction

-------------------------------------------------
stg_shop__order_lines

quy trình: bán hàng 
gain: 1 order + 1 line no là 1 đơn giá sản phẩm trong hóa đơn chính 
dimension: products code
measure: price per one product
loại fact: transaction


























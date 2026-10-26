-- Nguồn là bảng TRẠNG THÁI HIỆN TẠI: mỗi lần chạy chỉ thấy 1 dòng / đơn → satellite không cần lọc thêm.
{%- set yaml_metadata -%}
source_model: stg_shop__orders
derived_columns:
  RECORD_SOURCE: "!SHOP.ORDERS"
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: updated_at
hashed_columns:
  ORDER_HK: order_number
  CUSTOMER_HK: customer_code
  LINK_ORDER_CUSTOMER_HK: [order_number, customer_code]
  ORDER_SHOP_HASHDIFF:
    is_hashdiff: true
    columns: [channel, payment_method, is_gift, shipping_fee, total_amount, order_status, order_ts, paid_at, cancelled_at]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}

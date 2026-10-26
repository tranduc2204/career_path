-- Khách vãng lai (customer_code null) → "zero key" '-2' (null_columns: optional) để link luôn trỏ được tới hub.
-- Giá trị gốc giữ ở cột customer_code_ORIGINAL. order_number là cột dẫn xuất để hub_order gộp được 2 nguồn.
{%- set yaml_metadata -%}
source_model: stg_pos__sales
derived_columns:
  RECORD_SOURCE: "!POS.SALES"
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: sale_ts
  order_number: receipt_no
null_columns:
  optional:
    - customer_code
hashed_columns:
  ORDER_HK: order_number
  CUSTOMER_HK: customer_code
  PRODUCT_HK: sku
  LINK_ORDER_CUSTOMER_HK: [order_number, customer_code]
  ORDER_LINE_HK: [order_number, sku, line_no]
  ORDER_POS_HASHDIFF:
    is_hashdiff: true
    columns: [store_code, payment_method, sale_ts]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     null_columns=metadata['null_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}

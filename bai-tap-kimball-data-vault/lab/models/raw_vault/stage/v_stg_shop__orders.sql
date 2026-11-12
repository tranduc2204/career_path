{%- set yaml_metadata -%}
source_model: stg_shop__orders
derived_columns:
  RECORD_SOURCE: "!SHOP.ORDERS"              # dấu ! = hằng số chuỗi
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: "CAST(updated_at AS TIMESTAMP)"
hashed_columns:
  CUSTOMER_HK: customer_code
  ORDER_HK: order_number
  LINK_ORDER_CUSTOMER_HK: [order_number, customer_code] # link list nhiều cột
  ORDERS_SHOP_HASHDIFF:
    is_hashdiff: true
    columns: [channel, payment_method, is_gift, shipping_fee, total_amount, order_status, order_ts, paid_at, cancelled_at, order_status, paid_at, cancelled_at]
 
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}
{%- set yaml_metadata -%}
source_model: stg_shop__order_vouchers
derived_columns:
  RECORD_SOURCE: "!SHOP.ORDER_VOUCHERS"
  LOAD_DATETIME: _loaded_at
hashed_columns:
  ORDER_HK: order_number
  VOUCHER_HK: voucher_code
  ORDER_VOUCHER_HK: [order_number, voucher_code]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}

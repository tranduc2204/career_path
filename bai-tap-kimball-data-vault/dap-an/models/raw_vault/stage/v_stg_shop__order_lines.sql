{%- set yaml_metadata -%}
source_model: stg_shop__order_lines
derived_columns:
  RECORD_SOURCE: "!SHOP.ORDER_LINES"
  LOAD_DATETIME: _loaded_at
hashed_columns:
  ORDER_HK: order_number
  PRODUCT_HK: sku
  ORDER_LINE_HK: [order_number, sku, line_no]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}

{%- set yaml_metadata -%}
source_model: stg_crm__customers
derived_columns:
  RECORD_SOURCE: "!CRM.CUSTOMERS"              # dấu ! = hằng số chuỗi
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: "CAST(extract_date AS TIMESTAMP)"
hashed_columns:
  CUSTOMER_HK: customer_code
  CUSTOMER_PROFILE_HASHDIFF:
    is_hashdiff: true
    columns: [full_name, email]
  CUSTOMER_STATUS_HASHDIFF:
    is_hashdiff: true
    columns: [city, loyalty_tier]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}
{%- set yaml_metadata -%}
source_model: latest_crm__customer_phones
derived_columns:
  RECORD_SOURCE: "!CRM.CUSTOMER_PHONES"
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: "CAST(extract_date AS TIMESTAMP)"
hashed_columns:
  CUSTOMER_HK: customer_code
  PHONE_HASHDIFF:
    is_hashdiff: true
    columns: [phone_type, phone_number]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}

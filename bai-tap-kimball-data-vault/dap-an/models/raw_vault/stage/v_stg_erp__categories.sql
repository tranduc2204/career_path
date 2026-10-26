{%- set yaml_metadata -%}
source_model: stg_erp__categories
derived_columns:
  RECORD_SOURCE: "!ERP.CATEGORIES"
  LOAD_DATETIME: _loaded_at
  EFFECTIVE_FROM: _loaded_at
hashed_columns:
  CATEGORY_HK: category_code
  CATEGORY_HASHDIFF:
    is_hashdiff: true
    columns: [category_name, parent_code]
{%- endset -%}

{%- set metadata = fromyaml(yaml_metadata) -%}

{{ automate_dv.stage(include_source_columns=true,
                     source_model=metadata['source_model'],
                     derived_columns=metadata['derived_columns'],
                     hashed_columns=metadata['hashed_columns'],
                     ranked_columns=none) }}

-- S8 — dựng lại toàn bộ lịch sử từ CDC log, chạy lại bao nhiêu lần cũng ra cùng kết quả
{{ scd2_from_changelog(
    relation=ref('stg_customer_changelog'),
    key='customer_id',
    changed_at='changed_at',
    tracked_columns=['city', 'tier']
) }}

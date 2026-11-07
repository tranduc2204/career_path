-- Cảnh báo (không chặn) khi số dư tính từ giao dịch lệch sổ cái. Lệch thật phải được điều tra, không "sửa cho khớp".
{{ config(severity='warn') }}
select * from {{ ref('rpt_gl_reconciliation') }} where not is_matched

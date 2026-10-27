-- B10 bonus · Forward fill không dùng IGNORE NULLS (Postgres, Redshift cũ...)
-- COUNT(gia) lũy kế chỉ tăng khi gặp giá khác NULL → mọi dòng NULL phía sau cùng "nhóm" với
-- dòng có giá gần nhất. Lấy MAX(gia) trong nhóm = giá đó.
-- Back fill làm tương tự theo chiều ngược (ORDER BY ngay DESC).
with nhom as (
    select
        *,
        count(gia) over (partition by san_pham_id order by ngay
                         rows between unbounded preceding and current row) as nhom_xuoi,
        count(gia) over (partition by san_pham_id order by ngay desc
                         rows between unbounded preceding and current row) as nhom_nguoc
    from gia_niem_yet
)
select
    san_pham_id,
    ngay,
    coalesce(
        max(gia) over (partition by san_pham_id, nhom_xuoi),
        max(gia) over (partition by san_pham_id, nhom_nguoc)
    ) as gia_da_dien
from nhom

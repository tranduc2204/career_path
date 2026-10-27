with t as (
    select
        cua_hang,
        ngay,
        doanh_thu,
        -- "1 PRECEDING" ở đầu mút cuối = loại dòng hiện tại ra khỏi khung
        max(doanh_thu) over (
            partition by cua_hang
            order by ngay
            rows between unbounded preceding and 1 preceding
        ) as max_truoc_do
    from doanh_thu_ngay
)
select
    cua_hang,
    ngay,
    max_truoc_do,
    (max_truoc_do is null or doanh_thu > max_truoc_do) as la_ky_luc
from t

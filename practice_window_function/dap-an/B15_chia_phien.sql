with co_co as (
    select
        giao_dich_id,
        khach_hang_id,
        thoi_diem,
        case
            when lag(thoi_diem) over w is null then 1
            when thoi_diem - lag(thoi_diem) over w > interval 30 minutes then 1
            else 0
        end as phien_moi
    from giao_dich
    window w as (partition by khach_hang_id order by thoi_diem, giao_dich_id)
)
-- Ghi chú: ở bài này RANGE mặc định (ORDER BY thoi_diem) cũng ra đúng — trong 1 nhóm peer chỉ
-- có đúng 1 dòng mang cờ 1 (dòng đầu nhóm), các peer còn lại cách nhau 0 phút → cờ 0, nên cộng
-- cả nhóm peer không làm sai. Nhưng đó là "đúng nhờ tính chất dữ liệu"; viết ROWS + tie-breaker
-- để không phải suy luận như vậy.
select
    giao_dich_id,
    sum(phien_moi) over (
        partition by khach_hang_id
        order by thoi_diem, giao_dich_id
        rows between unbounded preceding and current row
    ) as phien_so
from co_co

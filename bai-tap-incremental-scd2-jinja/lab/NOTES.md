# số bảng tổng cộng
'''
| table_name         |
| ------------------ |
| _lab_log           |
| _lab_state         |
| customer_changelog |
| customers          |
| events             |
| order_items        |
| orders             |
| products           |
'''

các staging nên có stg__customers



# tình huống P1 là 
bảng stg order_xuất hiện duplicate.  
và bị báo lỗi uniquekey
cần sử dụng qualify để loại bỏ case deduplicate. 



# tình huống P2 là 
cột order ở ngày 7 bị xóa đi và cần sử dụng kĩ thuậtt để enable hay visble cột để fix lỗi này 
 {% if 'order_status' in source_columns %}
            order_status
        {% elif 'status' in source_columns %}
            status
        {% else %}
            cast(null as varchar) as order_status
        {% endif %}





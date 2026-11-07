-- Danh mục nguồn truy cập (utm_source). Dùng làm "conformed dimension" giữa đơn hàng, phiên và chi phí quảng cáo.
select * from (values
    ('google',   'Google Ads',   'paid'),
    ('facebook', 'Facebook Ads', 'paid'),
    ('tiktok',   'TikTok Ads',   'paid'),
    ('organic',  'Organic',      'organic'),
    ('email',    'Email CRM',    'owned')
) as t(utm_source, channel_name, channel_group)

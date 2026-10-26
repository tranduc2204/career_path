-- =====================================================================================================
-- 00. Chuẩn bị Snowflake cho thí nghiệm tuần 7 (chạy 1 lần, role ACCOUNTADMIN)
-- Tài liệu: https://docs.snowflake.com/en/user-guide/warehouses-overview
--           https://docs.snowflake.com/en/user-guide/resource-monitors
-- =====================================================================================================
use role accountadmin;

-- 1. Warehouse riêng cho thí nghiệm: tự tắt sau 60 giây rảnh
create warehouse if not exists perf_wh with
    warehouse_size = 'XSMALL'
    auto_suspend = 60
    auto_resume = true
    initially_suspended = true;

-- 2. Rào chắn: tối đa 10 credit / tháng cho warehouse này
create or replace resource monitor rm_perf_lab with
    credit_quota = 10
    frequency = monthly
    start_timestamp = immediately
    triggers
        on 50 percent do notify
        on 90 percent do suspend
        on 100 percent do suspend_immediate;

alter warehouse perf_wh set resource_monitor = rm_perf_lab;

-- 3. Nơi chứa bảng thí nghiệm
create database if not exists perf_lab;
create schema if not exists perf_lab.exp;

-- 4. Dữ liệu mẫu TPC-H thường có sẵn ở database SNOWFLAKE_SAMPLE_DATA. Nếu không thấy:
-- create database snowflake_sample_data from share sfc_samples.sample_data;
use warehouse perf_wh;
select count(*) from snowflake_sample_data.tpch_sf10.orders;      -- khoảng 15 triệu dòng

-- 5. ĐẦU MỖI PHIÊN thí nghiệm: tắt result cache để đo đúng, gắn tag để tìm lại query
use schema perf_lab.exp;
alter session set use_cached_result = false;
alter session set query_tag = 'perf_lab';

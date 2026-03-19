{{
    config(
        materialized='table'
    )
}}

with dates as (
    {{
        dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2005-05-01' as date)",
        end_date="cast('2006-03-01' as date)"
    )}}
),

final as (
    select
    {{dbt_utils.generate_surrogate_key(['date_day'])}} as date_key,
    date_day as date,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    extract(day from date_day) as day,
    extract(dow from date_day) as day_of_week,
    case when extract(dow from date_day) in (0,6) then 1 else 0 end as is_weekend
    from dates        
)
select * from final
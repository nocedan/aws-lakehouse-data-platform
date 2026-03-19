{{
    config(
        materialized='table'
    )
}}

with customer as (

    select * from {{ source('dvdrentals','customer')}}
)

select
    {{ dbt_utils.generate_surrogate_key(['customer_id'])}} as customer_key,
    customer_id,
    store_id,
    first_name,
    last_name,
    email,
    address_id,
    activebool,
    create_date,
    last_update,
    active
from customer
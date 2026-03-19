{{
    config(
        materialized='table'
    )
}}

with rental as (
    select * from {{ source('dvdrentals', 'rental') }}
),
inventory as (
    select * from {{ source('dvdrentals', 'inventory') }}
),
film as (
    select * from {{ source('dvdrentals', 'film') }}
),
fact_rentals as (
    select
        -- keys
        {{ dbt_utils.generate_surrogate_key(['rental.rental_id']) }}    as rental_key,
        rental.rental_id,
        {{ dbt_utils.generate_surrogate_key(['rental.customer_id']) }}  as customer_key,
        --{{ dbt_utils.generate_surrogate_key(['rental.inventory_id']) }} as inventory_key,
        {{ dbt_utils.generate_surrogate_key(['inventory.film_id']) }}      as film_key,
        {{ dbt_utils.generate_surrogate_key(['rental.rental_date']) }}  as rental_date_key,
        {{ dbt_utils.generate_surrogate_key(['rental.return_date']) }}  as return_date_key,

        -- facts
        film.rental_duration                                                          as rental_duration_expected,
        extract(day from (rental.return_date - rental.rental_date))                   as rental_duration_actual,
        extract(day from (rental.return_date - rental.rental_date))
            - film.rental_duration                                                    as delay_days,
        case
            when extract(day from (rental.return_date - rental.rental_date))
                > film.rental_duration
            then 1 else 0
        end                                                                           as is_delayed

    from rental
    left join inventory on rental.inventory_id = inventory.inventory_id
    left join film      on inventory.film_id    = film.film_id
)

select * from fact_rentals
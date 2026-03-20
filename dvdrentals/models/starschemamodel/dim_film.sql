{{
  config(
    materialized='table'
  )
}}

with film as (
  select * from {{ source('dvdrentals','film')}}
),
film_category as (
 select * from {{source('dvdrentals','film_category')}}
 ),
 category as (
  select * from {{source('dvdrentals','category')}}
 ),
joined as (
 select
film.*,
film_category.category_id,
film_category.last_update as film_category_last_update,
category.name as category_name
from film join film_category on film.film_id = film_category.film_id
left join category on film_category.category_id = category.category_id
)
select 
  {{ dbt_utils.generate_surrogate_key(['film_id']) }} as film_key,
  film_id,
  title,
  description,
  release_year,
  rental_duration,
  rental_rate,
  length,
  replacement_cost,
  rating,
  last_update,
  category_id,
  film_category_last_update,
  category_name
from joined
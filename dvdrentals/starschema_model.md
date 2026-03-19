# Star Schema — dvdrentals

## Tabelas de origem

As tabelas utilizadas do database **dvdrentals** são:

- `inventory`
- `film_category`
- `customer`
- `film`
- `rental`
- `category`

---

## Dimensões e Fato

A partir dessas tabelas serão produzidas as dimensões:

- `dim_film`
- `dim_customer`
- `dim_dates`

e a tabela fato `fact_rentals`.

---

## dim_film

| Coluna | Tipo / Papel |
|---|---|
| `film_key` | PK (surrogate key) |
| `film_id` | NK (natural key) |
| `title` | |
| `description` | |
| `release_year` | |
| `rental_duration` | dias permitidos de locação |
| `rental_rate` | |
| `length` | |
| `replacement_cost` | |
| `rating` | |
| `last_update` | |
| `category_id` | FK → `category` |
| `film_category_last_update` | |

---

## dim_customer

| Coluna | Tipo / Papel |
|---|---|
| `customer_key` | PK (surrogate key) |
| `customer_id` | NK (natural key) |
| `store_id` | |
| `first_name` | |
| `last_name` | |
| `email` | |
| `address_id` | |
| `activebool` | |
| `create_date` | |
| `last_update` | |
| `active` | |

---

## dim_dates

| Coluna | Tipo / Papel |
|---|---|
| `date_key` | PK (surrogate key) |
| `full_date` | data completa |
| `day_of_week` | |
| `day_of_month` | |
| `month` | |
| `quarter` | |
| `year` | |
| `is_weekend` | |

> **Nota:** `rental_date` e `return_date` são atributos de `fact_rentals` que referenciam `dim_dates` via FK — não colunas da própria dimensão.

---

## fact_rentals

| Coluna | Tipo / Papel |
|---|---|
| `rental_key` | PK (surrogate key) |
| `rental_id` | NK (natural key) |
| `customer_key` | FK → `dim_customer` |
| `film_key` | FK → `dim_film` |
| `rental_date_key` | FK → `dim_dates` |
| `return_date_key` | FK → `dim_dates` |

### Medidas

| Coluna | Descrição |
|---|---|
| `rental_duration_expected` | duração prevista da locação (dias), vinda de `film.rental_duration` |
| `rental_duration_actual` | duração real da locação (dias), calculada como `return_date − rental_date` |
| `delay_days` | dias de atraso (`rental_duration_actual − rental_duration_expected`); 0 se negativo |
| `is_delayed` | booleano — `true` se `delay_days > 0` |

-- EXCEPT ALL in both directions detects lost rows, fanout and any changed Clean field.
{% set columns = 'deal_id, snapshot_timestamp, snapshot_date, store, store_normalized, title, title_link, deal_path, deal_finder, deal_finder_normalized, editors_note, deal_price_raw, deal_price_type, deal_price_amount, original_price_raw, original_price_amount, discount_percentage, price_parse_success, comment_count, vote_count, views, page_section, card_layout, record_position, record_position_source, dom_position, section_position, card_badge, raw_schema_version, parser_version, data_scope, candidate_records, omitted_count, is_truncated, snapshot_timestamp_source, source_file, pipeline_run_id, record_hash' %}
with clean as (select {{ columns }} from {{ ref('stg_clean_observation') }}),
fact as (select {{ columns }} from {{ ref('fct_deal_observation') }})
(select * from clean except all select * from fact)
union all
(select * from fact except all select * from clean)

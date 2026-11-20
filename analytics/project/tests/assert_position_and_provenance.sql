select deal_id, snapshot_timestamp from {{ ref('stg_clean_observation') }}
where snapshot_date is distinct from snapshot_timestamp::date or record_position is null
   or store_normalized is null or store_normalized = '' or title_link is null
   or not coalesce(regexp_full_match(record_hash, '[0-9a-f]{64}'), false)
   or (raw_schema_version = 1 and (record_position_source is distinct from 'recovered_json_array_order'
       or dom_position is not null or section_position is not null))
   or (raw_schema_version = 2 and (record_position_source is distinct from 'parser'
       or dom_position is null or section_position is null))

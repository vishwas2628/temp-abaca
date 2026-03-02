/*
  Upon upgrading PostgreSQL from 9.6 to 13
  the empty string comparison (::text = ''::text on lines 38 - 40)
  no longer works for nullable values hence this fix (is null):
*/
drop view if exists matching.match_location_view;
create or replace view matching.match_location_view(company_id, supporter_id, weight_id, default_score, is_unanswered, is_match) as
with entrepreneurs_locations as (
         select
             vcl.company_id,
             vl.continent,
             vl.country,
             vl.city,
             vl.region
         from viral_company_locations vcl
                  join viral_location vl on vcl.location_id = vl.id),
     supporters_locations as (
        select
        msl.supporter_id,
        vl.continent,
        vl.country,
        vl.city,
        vl.region
        from matching_supporter_locations msl
        join viral_location vl on msl.location_id = vl.id)
select esv.company_id,
       esv.supporter_id,
       esv.location_weight_id                                                                                           as weight_id,
       esv.location_score                                                                                               as default_score,
       not (exists(select el.company_id from entrepreneurs_locations el where el.company_id = esv.company_id))          as is_unanswered,
       (not (exists(select sl.supporter_id from supporters_locations sl where sl.supporter_id = esv.supporter_id))
            and exists(select el.company_id from entrepreneurs_locations el where el.company_id = esv.company_id))
        or exists(
            select sl.supporter_id
            from entrepreneurs_locations el
            left join supporters_locations sl
                on sl.country::text = el.country::text
                    and (sl.continent::text = el.continent::text OR sl.continent is null OR sl.continent::text = ''::text)
                    and (sl.city::text = el.city::text OR sl.city is null OR sl.city::text = ''::text)
                    and (sl.region::text = el.region::text OR sl.region is null OR sl.region::text = ''::text)
            where sl.supporter_id = esv.supporter_id and el.company_id = esv.company_id)                                as is_match
from matching.entrepreneur_supporter_view esv;
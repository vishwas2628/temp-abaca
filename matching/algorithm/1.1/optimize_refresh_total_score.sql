-- 1. Add replacement function for the uneficient active_total_scores_view
create or replace function matching.get_active_total_score(_refresh_all boolean DEFAULT true, _company_id integer DEFAULT '-1'::integer, _supporter_id integer DEFAULT '-1'::integer)
    returns TABLE(company_id integer, supporter_id integer, score bigint, max_score bigint, max_score_percentil numeric)
    language plpgsql
as
$$
begin
    return query
    WITH scores AS (
        SELECT location_score.company_id,
               location_score.supporter_id,
               location_score.score,
               location_score.max_score,
               location_score.created_at
        FROM matching.location_score
        where (
          _refresh_all 
          or _company_id > -1 and location_score.company_id = _company_id 
          or _supporter_id > -1 and location_score.supporter_id = _supporter_id)
        UNION ALL
        SELECT level_score.company_id,
               level_score.supporter_id,
               level_score.score,
               level_score.max_score,
               level_score.created_at
        FROM matching.level_score
        where (
          _refresh_all 
          or _company_id > -1 and level_score.company_id = _company_id 
          or _supporter_id > -1 and level_score.supporter_id = _supporter_id)
        UNION ALL
        SELECT sector_score.company_id,
               sector_score.supporter_id,
               sector_score.score,
               sector_score.max_score,
               sector_score.created_at
        FROM matching.sector_score
        where (
          _refresh_all 
          or _company_id > -1 and sector_score.company_id = _company_id 
          or _supporter_id > -1 and sector_score.supporter_id = _supporter_id)
        UNION ALL
        SELECT response_score.company_id,
               response_score.supporter_id,
               response_score.score,
               response_score.max_score,
               response_score.created_at
        FROM matching.response_score
        where (
          _refresh_all 
          or _company_id > -1 and response_score.company_id = _company_id 
          or _supporter_id > -1 and response_score.supporter_id = _supporter_id)
    ),
         l AS (
             SELECT esv.company_id,
                    esv.supporter_id,
                    sum(s.score)     AS score,
                    sum(s.max_score) AS max_score
             FROM matching.entrepreneur_supporter_view esv
                      JOIN scores s ON s.company_id = esv.company_id AND s.supporter_id = esv.supporter_id
             GROUP BY esv.company_id, esv.supporter_id
         ),
         total_scores AS (
             SELECT DISTINCT l.company_id,
                             l.supporter_id,
                             l.score,
                             l.max_score,
                             CASE WHEN l.max_score = 0 THEN 100
                                ELSE GREATEST(round((l.score * 100 / l.max_score)::numeric, 0), 0::numeric) 
                             END AS max_score_percentil
             FROM l
         )
    SELECT ts.company_id,
           ts.supporter_id,
           ts.score,
           ts.max_score,
           ts.max_score_percentil
    FROM total_scores ts
    WHERE ts.max_score_percentil > 0::numeric
       OR (EXISTS(SELECT 1
                  FROM matching_interestedcta
                  WHERE matching_interestedcta.entrepreneur_id = ts.company_id
                    AND matching_interestedcta.supporter_id = ts.supporter_id
                    AND matching_interestedcta.state_of_interest <> 0));

end;
$$;
-- 2. Alter refresh_total_score
create or replace function matching.refresh_total_score(_refresh_all boolean DEFAULT true, _company_id integer DEFAULT '-1'::integer, _supporter_id integer DEFAULT '-1'::integer) returns void
    language plpgsql
as
$$
begin
    -- Remove old scores
    if _refresh_all = true then
        truncate matching.total_score;
    else
        delete from matching.total_score
        where _company_id > -1 and company_id = _company_id
        or _supporter_id > -1 and supporter_id = _supporter_id;
    end if;

    -- Process new total scores
    insert into matching.total_score
    select *
    from matching.get_active_total_score(_refresh_all, _company_id, _supporter_id) as t;
end;
$$;
-- 3. Drop active_total_scores_views
drop view if exists matching.active_total_scores_view;

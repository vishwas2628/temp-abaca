create or replace view matching.active_total_scores_view(company_id, supporter_id, score, max_score, max_score_percentil) as
WITH scores AS (
    SELECT location_score.company_id,
           location_score.supporter_id,
           location_score.score,
           location_score.max_score,
           location_score.created_at
    FROM matching.location_score
    UNION ALL
    SELECT level_score.company_id,
           level_score.supporter_id,
           level_score.score,
           level_score.max_score,
           level_score.created_at
    FROM matching.level_score
    UNION ALL
    SELECT sector_score.company_id,
           sector_score.supporter_id,
           sector_score.score,
           sector_score.max_score,
           sector_score.created_at
    FROM matching.sector_score
    UNION ALL
    SELECT response_score.company_id,
           response_score.supporter_id,
           response_score.score,
           response_score.max_score,
           response_score.created_at
    FROM matching.response_score
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
                greatest(round((l.score * 100 / l.max_score)::numeric, 0), 0) AS max_score_percentil
  FROM l
  WHERE l.max_score > 0
)
SELECT *
FROM total_scores ts
WHERE max_score_percentil > 0
    OR EXISTS(
        -- Keep existing zero scores where there's an existing interest
        SELECT 1
        FROM public.matching_interestedcta
        WHERE entrepreneur_id = ts.company_id
            AND supporter_id = ts.supporter_id
            AND state_of_interest <> 0);

create or replace view matching.entrepreneur_supporter_view
            (company_id, supporter_id, supporter_level_range, sector_weight_id, sector_score, level_weight_id,
             level_score, location_weight_id, location_score)
as
SELECT          vc.id                    AS company_id,
                ms.id                    AS supporter_id,
                ms.investing_level_range AS supporter_level_range,
                ms.sectors_weight_id     AS sector_weight_id,
                cw.value                 AS sector_score,
                ms.level_weight_id,
                cw1.value                AS level_score,
                ms.locations_weight_id   AS location_weight_id,
                cw2.value                AS location_score
FROM (SELECT vc_1.id
      FROM viral_company vc_1
      WHERE vc_1.type = 0) vc,
     matching_supporter ms
         LEFT JOIN matching_criteriaweight cw ON cw.id = ms.sectors_weight_id
         LEFT JOIN matching_criteriaweight cw1 ON cw1.id = ms.level_weight_id
         LEFT JOIN matching_criteriaweight cw2 ON cw2.id = ms.locations_weight_id;


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
)
SELECT          l.company_id,
                l.supporter_id,
                l.score,
                l.max_score,
                round((l.score * 100 / l.max_score)::numeric, 0) AS max_score_percentil
FROM (SELECT s.company_id,
             s.supporter_id,
             sum(s.score)     AS score,
             sum(s.max_score) AS max_score
      FROM scores s
      GROUP BY s.company_id, s.supporter_id) l
WHERE l.score > 0;

create or replace view matching.match_location_view(company_id, supporter_id, weight_id, default_score, is_match) as
SELECT          esv.company_id,
                esv.supporter_id,
                esv.location_weight_id     AS weight_id,
                esv.location_score         AS default_score,
                esl.company_id IS NOT NULL AS is_match
FROM matching.entrepreneur_supporter_view esv
         LEFT JOIN (SELECT cl.company_id,
                           sl.supporter_id
                    FROM (SELECT vcl.company_id,
                                 vl.continent,
                                 vl.country,
                                 vl.city,
                                 vl.region
                          FROM viral_company_locations vcl
                                   JOIN viral_location vl ON vcl.location_id = vl.id) cl
                             JOIN (SELECT msl.supporter_id,
                                          vl.continent,
                                          vl.country,
                                          vl.city,
                                          vl.region
                                   FROM matching_supporter_locations msl
                                            JOIN viral_location vl ON msl.location_id = vl.id) sl
                                  ON sl.country::text = cl.country::text AND
                                     (sl.continent::text = cl.continent::text OR sl.continent::text = ''::text) AND
                                     (sl.city::text = cl.city::text OR sl.city::text = ''::text) AND
                                     (sl.region::text = cl.region::text OR sl.region::text = ''::text)) esl
                   ON esl.company_id = esv.company_id AND esl.supporter_id = esv.supporter_id;
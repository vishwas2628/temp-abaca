/* 
 * Exclude Entrepreneurs without VIRAL level
*/
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
         LEFT JOIN matching_criteriaweight cw2 ON cw2.id = ms.locations_weight_id
WHERE EXISTS(SELECT evaluated FROM grid_assessment WHERE evaluated = vc.id);

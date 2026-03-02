create schema if not exists matching;

-- Views

create or replace view matching.entrepreneur_supporter_view
            (company_id, supporter_id, supporter_level_range, sector_weight_id, sector_score, level_weight_id,
             level_score, location_weight_id, location_score)
as
SELECT DISTINCT vc.id                    AS company_id,
                ms.id                    AS supporter_id,
                ms.investing_level_range AS supporter_level_range,
                ms.sectors_weight_id     AS sector_weight_id,
                cw.value                 AS sector_score,
                ms.level_weight_id,
                cw1.value                AS level_score,
                ms.locations_weight_id   AS location_weight_id,
                cw2.value                AS location_score
FROM (SELECT vc.id
      FROM public.viral_company vc
      WHERE vc.type = 0) vc,
     public.matching_supporter ms
         LEFT JOIN public.matching_criteriaweight cw ON cw.id = ms.sectors_weight_id
         LEFT JOIN public.matching_criteriaweight cw1 ON cw1.id = ms.level_weight_id
         LEFT JOIN public.matching_criteriaweight cw2 ON cw2.id = ms.locations_weight_id;

create or replace view matching.exclusion_match_quantity_view(company_id, type, match_quantity) as
SELECT mq.company_id,
       mq.type,
       mq.match_quantity
FROM (SELECT vc.id            AS company_id,
             vc.type,
             sum(
                     CASE
                         WHEN s.max_score_percentil IS NULL THEN 0
                         ELSE 1
                         END) AS match_quantity
      FROM public.matching_supporter ms
               JOIN public.viral_userprofile vu ON ms.user_profile_id = vu.id
               JOIN public.viral_company vc ON vu.company_id = vc.id
               LEFT JOIN matching.exclusion_total_score s ON s.supporter_id = ms.id
      GROUP BY vc.id, vc.type
      UNION ALL
      SELECT vc.id            AS company_id,
             vc.type,
             sum(
                     CASE
                         WHEN s.max_score_percentil IS NULL THEN 0
                         ELSE 1
                         END) AS match_quantity
      FROM public.viral_company vc
               LEFT JOIN matching.exclusion_total_score s ON s.company_id = vc.id
      WHERE vc.type = 0
      GROUP BY vc.id, vc.type) mq
ORDER BY mq.company_id;

create or replace view matching.initial_match_quantity_view(company_id, type, match_quantity) as
SELECT mq.company_id,
       mq.type,
       mq.match_quantity
FROM (SELECT vc.id            AS company_id,
             vc.type,
             sum(
                     CASE
                         WHEN s.max_score_percentil IS NULL THEN 0
                         ELSE 1
                         END) AS match_quantity
      FROM public.matching_supporter ms
               JOIN public.viral_userprofile vu ON ms.user_profile_id = vu.id
               JOIN public.viral_company vc ON vu.company_id = vc.id
               LEFT JOIN matching.initial_total_score s ON s.supporter_id = ms.id
      GROUP BY vc.id, vc.type
      UNION ALL
      SELECT vc.id            AS company_id,
             vc.type,
             sum(
                     CASE
                         WHEN s.max_score_percentil IS NULL THEN 0
                         ELSE 1
                         END) AS match_quantity
      FROM public.viral_company vc
               LEFT JOIN matching.initial_total_score s ON s.company_id = vc.id
      WHERE vc.type = 0
      GROUP BY vc.id, vc.type) mq
ORDER BY mq.company_id;

create or replace view matching.latest_assessments_view(company_id, company_level) as
SELECT latest.company_id,
       latest.company_level
FROM (SELECT ga.evaluated                                                              AS company_id,
             gl.value                                                                  AS company_level,
             row_number() OVER (PARTITION BY ga.evaluated ORDER BY ga.created_at DESC) AS entry_number
      FROM public.grid_assessment ga
               JOIN public.grid_level gl ON gl.id = ga.level_id) latest
WHERE latest.entry_number = 1;

create or replace view matching.match_location_view(company_id, supporter_id, weight_id, default_score, is_match) as
SELECT DISTINCT esv.company_id,
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
                          FROM public.viral_company_locations vcl
                                   JOIN public.viral_location vl ON vcl.location_id = vl.id) cl
                             JOIN (SELECT msl.supporter_id,
                                          vl.continent,
                                          vl.country,
                                          vl.city,
                                          vl.region
                                   FROM public.matching_supporter_locations msl
                                            JOIN public.viral_location vl ON msl.location_id = vl.id) sl
                                  ON sl.country::text = cl.country::text AND
                                     (sl.continent::text = cl.continent::text OR sl.continent::text = ''::text) AND
                                     (sl.city::text = cl.city::text OR sl.city::text = ''::text) AND
                                     (sl.region::text = cl.region::text OR sl.region::text = ''::text)) esl
                   ON esl.company_id = esv.company_id AND esl.supporter_id = esv.supporter_id;

create or replace view matching.match_sector_view(company_id, supporter_id, weight_id, default_score, is_match) as
SELECT esv.company_id,
       esv.supporter_id,
       esv.sector_weight_id                                                                                                    AS weight_id,
       esv.sector_score                                                                                                        AS default_score,
       NOT (EXISTS(SELECT mss.id
                   FROM public.matching_supporter_sectors mss
                   WHERE mss.supporter_id = esv.supporter_id)) OR
       (EXISTS(SELECT vcs.id
               FROM public.viral_company_sectors vcs
               WHERE vcs.company_id = esv.company_id
                 AND (vcs.sector_id IN (SELECT mss.sector_id
                                        FROM public.matching_supporter_sectors mss
                                        WHERE mss.supporter_id = esv.supporter_id)))) AS is_match
FROM matching.entrepreneur_supporter_view esv;

create or replace view matching.penalisation_match_quantity_view(company_id, type, match_quantity) as
SELECT mq.company_id,
       mq.type,
       mq.match_quantity
FROM (SELECT vc.id            AS company_id,
             vc.type,
             sum(
                     CASE
                         WHEN s.max_score_percentil IS NULL THEN 0
                         ELSE 1
                         END) AS match_quantity
      FROM public.matching_supporter ms
               JOIN public.viral_userprofile vu ON ms.user_profile_id = vu.id
               JOIN public.viral_company vc ON vu.company_id = vc.id
               LEFT JOIN matching.penalisation_total_score s ON s.supporter_id = ms.id
      GROUP BY vc.id, vc.type
      UNION ALL
      SELECT vc.id            AS company_id,
             vc.type,
             sum(
                     CASE
                         WHEN s.max_score_percentil IS NULL THEN 0
                         ELSE 1
                         END) AS match_quantity
      FROM public.viral_company vc
               LEFT JOIN matching.penalisation_total_score s ON s.company_id = vc.id
      WHERE vc.type = 0
      GROUP BY vc.id, vc.type) mq
ORDER BY mq.company_id;


-- Trigger

create or replace function matching.algorithm_update()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    new.updated_at = now();

    if new.active = true then
        update matching.algorithm
        set active = false
        where id != new.id;

        -- Execute refresh only if all criterias are initialized
        if (
               select count(1)
               from
                   (
                       select count(1)
                       from matching.algorithm a
                                join public.matching_criteriaweight mc
                                     on a.level_weight_id = mc.id
                       where a.active
                       union
                       select count(1)
                       from matching.algorithm a
                                join public.matching_criteriaweight mc
                                     on a.location_weight_id = mc.id
                       where a.active
                       union
                       select count(1)
                       from matching.algorithm a
                                join public.matching_criteriaweight mc
                                     on a.sector_weight_id = mc.id
                       where a.active
                       union
                       select count(1)
                       from matching.algorithm a
                                join public.matching_criteriaweight mc
                                     on a.response_weight_id = mc.id
                       where a.active) t
               where count = 0) = 0
        then
            perform matching.refresh_level_score();
            perform matching.refresh_sector_score();
            perform matching.refresh_location_score();
            perform matching.refresh_response_score();
            perform matching.refresh_total_score();
        end if;
    end if;

    return new;
end;
$$;


-- Function


-- add new algorithm settings

create or replace function matching.algorithm_update() returns trigger
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
    end if;

    return new;
end;
$$;

alter table matching.algorithm
    add column unanswered_factor float default 0,
    add column high_unanswered_factor float default 0,
    add column wrong_factor float default 0,
    add column high_wrong_factor float default 0;

update matching.algorithm
set unanswered_factor = 0, wrong_factor = 0, high_unanswered_factor = 0.5, high_wrong_factor = 0.5
where id = 3;

update matching.algorithm
set unanswered_factor = 1, wrong_factor = 1, high_unanswered_factor = 1000, high_wrong_factor = 1000
where id = 2;

alter table matching.algorithm
drop column if exists prefix;

insert into matching.algorithm(name, active, level_weight_id, location_weight_id, sector_weight_id, response_weight_id, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor)
values ('penalisation@1.0.1', false, 4, 5, 5, 1, 0, 0.3, 0, 0.5);


-- alter levels calculation

drop view if exists matching.match_assessment_view;
create or replace view matching.match_assessment_view(company_id, supporter_id, weight_id, default_score, is_match, is_unanswered) as
select esv.company_id,
       esv.supporter_id,
       esv.level_weight_id                                                                                          AS weight_id,
       esv.level_score                                                                                              AS default_score,
       la.company_level = lower(esv.supporter_level_range) OR la.company_level >= lower(esv.supporter_level_range) AND
                                                              la.company_level < upper(esv.supporter_level_range)   AS is_match,
       la.company_level is null as is_unanswered
from matching.entrepreneur_supporter_view esv
         left join matching.latest_assessments_view la ON la.company_id = esv.company_id;

create or replace function matching.get_levels(alg_weight_id integer, alg_score integer, unanswered_factor float, high_unanswered_factor float, wrong_factor float, high_wrong_factor float)
    returns TABLE(company_id integer, supporter_id integer, score integer, max_score integer)
    language plpgsql
as
$$
begin
    return query
        select
            l.company_id,
            l.supporter_id,
            l.score,
            l.max_score
        from (
                 select am.*,
                        (case
                             when am.is_match
                                 then coalesce(am.default_score, alg_score)
                             when coalesce(am.weight_id, alg_weight_id) = 5 and am.is_unanswered
                                 then -coalesce(am.default_score, alg_score) * high_unanswered_factor
                             when am.is_unanswered
                                 then -coalesce(am.default_score, alg_score) * unanswered_factor
                             when coalesce(am.weight_id, alg_weight_id) = 5
                                 then -coalesce(am.default_score, alg_score) * high_wrong_factor
                             else -coalesce(am.default_score, alg_score) * wrong_factor
                            end)::numeric::integer            as score,
                        coalesce(am.default_score, alg_score) as max_score
                 from matching.match_assessment_view am) as l;
end;
$$;

create or replace function matching.refresh_level_score(_refresh_all boolean DEFAULT true, _company_id integer DEFAULT '-1'::integer, _supporter_id integer DEFAULT '-1'::integer) returns void
    language plpgsql
as
$$
declare
    alg_weight_id               integer;
    alg_score                   integer;
    unanswered_factor           float;
    high_unanswered_factor      float;
    wrong_factor                float;
    high_wrong_factor           float;
begin
    -- Remove old scores
    if _refresh_all = true then
        truncate matching.level_score;
    else
        delete from matching.level_score
        where company_id = _company_id or supporter_id = _supporter_id;
    end if;

    -- Get active algorithm settings
    select a.level_weight_id, mc.value, a.unanswered_factor, a.high_unanswered_factor, a.wrong_factor, a.high_wrong_factor
    into alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor
    from matching.algorithm a
             join public.matching_criteriaweight mc on a.level_weight_id = mc.id
    where a.active;

    -- Insert new values
    insert into matching.level_score (company_id, supporter_id, score, max_score)
    select vw.company_id, vw.supporter_id, vw.score, vw.max_score
    from matching.get_levels(alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor) as vw
    where (_refresh_all OR vw.company_id = _company_id OR vw.supporter_id = _supporter_id);
end;
$$;


-- alter locations calculation

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
                    and (sl.continent::text = el.continent::text OR sl.continent::text = ''::text)
                    and (sl.city::text = el.city::text OR sl.city::text = ''::text)
                    and (sl.region::text = el.region::text OR sl.region::text = ''::text)
            where sl.supporter_id = esv.supporter_id and el.company_id = esv.company_id)                                as is_match
from matching.entrepreneur_supporter_view esv;

create or replace function matching.get_locations(alg_weight_id integer, alg_score integer, unanswered_factor float, high_unanswered_factor float, wrong_factor float, high_wrong_factor float)
    returns TABLE(company_id integer, supporter_id integer, score integer, max_score integer)
    language plpgsql
as
$$
begin
    return query
        select
            l.company_id,
            l.supporter_id,
            l.score,
            l.max_score
        from (
                 select am.*,
                        (case
                             when am.is_match
                                 then coalesce(am.default_score, alg_score)
                             when coalesce(am.weight_id, alg_weight_id) = 5 and am.is_unanswered
                                 then -coalesce(am.default_score, alg_score) * high_unanswered_factor
                             when am.is_unanswered
                                 then -coalesce(am.default_score, alg_score) * unanswered_factor
                             when coalesce(am.weight_id, alg_weight_id) = 5
                                 then -coalesce(am.default_score, alg_score) * high_wrong_factor
                             else -coalesce(am.default_score, alg_score) * wrong_factor
                            end)::numeric::integer                                                      as score,
                        coalesce(am.default_score, alg_score)::numeric::integer                         as max_score
                 from matching.match_location_view am) as l;
end;
$$;

create or replace function matching.refresh_location_score(_refresh_all boolean DEFAULT true, _company_id integer DEFAULT '-1'::integer, _supporter_id integer DEFAULT '-1'::integer) returns void
    language plpgsql
as
$$
declare
    alg_weight_id               integer;
    alg_score                   integer;
    unanswered_factor           float;
    high_unanswered_factor      float;
    wrong_factor                float;
    high_wrong_factor           float;
begin
    -- Remove old scores
    if _refresh_all = true then
        truncate matching.location_score;
    else
        delete from matching.location_score
        where company_id = _company_id or supporter_id = _supporter_id;
    end if;

    -- Get active algorithm settings
    select a.level_weight_id, mc.value, a.unanswered_factor, a.high_unanswered_factor, a.wrong_factor, a.high_wrong_factor
    into alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor
    from matching.algorithm a
             join public.matching_criteriaweight mc
                  on a.location_weight_id = mc.id
    where a.active;

    -- Insert new values
    insert into matching.location_score (company_id, supporter_id, score, max_score)
    select vw.company_id, vw.supporter_id, vw.score, vw.max_score
    from matching.get_locations(alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor) as vw
    where (_refresh_all OR vw.company_id = _company_id OR vw.supporter_id = _supporter_id);
end;
$$;


-- alter sectors calculation

drop view if exists matching.match_sector_view;
create or replace view matching.match_sector_view(company_id, supporter_id, weight_id, default_score, is_unanswered, is_match) as
select
        esv.company_id,
        esv.supporter_id,
        esv.sector_weight_id                                                                                                    as weight_id,
        esv.sector_score                                                                                                        as default_score,
        not (EXISTS(select vcs.id from viral_company_sectors vcs where vcs.company_id = esv.company_id))                        as is_unanswered,
        (not (exists(select mss.id from matching_supporter_sectors mss where mss.supporter_id = esv.supporter_id))
                and exists(select vcs.id from viral_company_sectors vcs where vcs.company_id = esv.company_id))
           or (exists(select vcs.id from viral_company_sectors vcs where vcs.company_id = esv.company_id
                                                                     and (vcs.sector_id in (select mss.sector_id
                                                                     from matching_supporter_sectors mss
                                                                     where mss.supporter_id = esv.supporter_id))))              as is_match
from matching.entrepreneur_supporter_view esv;

create or replace function matching.get_sectors(alg_weight_id integer, alg_score integer, unanswered_factor float, high_unanswered_factor float, wrong_factor float, high_wrong_factor float)
    returns TABLE(company_id integer, supporter_id integer, score integer, max_score integer)
    language plpgsql
as
$$
begin
    return query
        select
            l.company_id,
            l.supporter_id,
            l.score,
            l.max_score
        from (
                 select am.*,
                        (case
                             when am.is_match
                                 then coalesce(am.default_score, alg_score)
                             when coalesce(am.weight_id, alg_weight_id) = 5 and am.is_unanswered
                                 then -coalesce(am.default_score, alg_score) * high_unanswered_factor
                             when am.is_unanswered
                                 then -coalesce(am.default_score, alg_score) * unanswered_factor
                             when coalesce(am.weight_id, alg_weight_id) = 5
                                 then -coalesce(am.default_score, alg_score) * high_wrong_factor
                             else -coalesce(am.default_score, alg_score) * wrong_factor
                            end)::numeric::integer                               as score,
                        coalesce(am.default_score, alg_score) as max_score
                 from matching.match_sector_view am) as l;
end;
$$;

create or replace function matching.refresh_sector_score(_refresh_all boolean DEFAULT true, _company_id integer DEFAULT '-1'::integer, _supporter_id integer DEFAULT '-1'::integer) returns void
    language plpgsql
as
$$
declare
    alg_weight_id integer;
    alg_score     integer;
    unanswered_factor           float;
    high_unanswered_factor      float;
    wrong_factor                float;
    high_wrong_factor           float;
begin
    -- Remove old scores
    if _refresh_all = true then
        truncate matching.sector_score;
    else
        delete from matching.sector_score
        where company_id = _company_id or supporter_id = _supporter_id;
    end if;

    -- Get active algorithm settings
    select a.level_weight_id, mc.value, a.unanswered_factor, a.high_unanswered_factor, a.wrong_factor, a.high_wrong_factor
    into alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor
    from matching.algorithm a
             join public.matching_criteriaweight mc
                  on a.location_weight_id = mc.id
    where a.active;

    -- Insert new values
    insert into matching.sector_score (company_id, supporter_id, score, max_score)
    select vw.company_id, vw.supporter_id, vw.score, vw.max_score
    from matching.get_sectors(alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor) as vw
    where (_refresh_all OR vw.company_id = _company_id OR vw.supporter_id = _supporter_id);
end;
$$;


-- alter responses calculation

create or replace function matching.get_responses(alg_weight_id integer, alg_score integer, unanswered_factor float, high_unanswered_factor float, wrong_factor float, high_wrong_factor float)
    returns TABLE(company_id integer, supporter_id integer, score integer, max_score integer)
    language plpgsql
as
$$
begin
    return query
        select
            l.company_id,
            l.supporter_id,
            l.score,
            l.max_score
        from (
        select esv.company_id,
               esv.supporter_id,
               sum(case
                       when am.is_correct
                           then coalesce(am.default_score, alg_score)
                       when coalesce(am.weight_id, alg_weight_id) = 5 and am.company_id is null
                           then -coalesce(am.default_score, alg_score) * high_unanswered_factor
                       when am.company_id is null
                           then -coalesce(am.default_score, alg_score) * unanswered_factor
                       when coalesce(am.weight_id, alg_weight_id) = 5
                           then -coalesce(am.default_score, alg_score) * high_wrong_factor
                       else -coalesce(am.default_score, alg_score) * wrong_factor
                   end)::numeric::integer as score,
               sum(coalesce(qc.score, alg_score))::integer as max_score
        from matching.entrepreneur_supporter_view esv
                 join matching.question_criteria_view qc
                      on qc.supporter_id = esv.supporter_id
                 left join matching.match_response_view am
                           on am.supporter_id = esv.supporter_id
                               and am.company_id = esv.company_id
                               and qc.question_id = am.question_id
        group by esv.company_id, esv.supporter_id) l;
end;
$$;

create or replace function matching.refresh_response_score(_refresh_all boolean DEFAULT true, _company_id integer DEFAULT '-1'::integer, _supporter_id integer DEFAULT '-1'::integer) returns void
    language plpgsql
as
$$
declare
    alg_weight_id integer;
    alg_score     integer;
    unanswered_factor           float;
    high_unanswered_factor      float;
    wrong_factor                float;
    high_wrong_factor           float;
begin
    -- Remove old scores
    if _refresh_all = true then
        truncate matching.response_score;
    else
        delete from matching.response_score
        where company_id = _company_id or supporter_id = _supporter_id;
    end if;

    -- Get active algorithm settings
    select a.level_weight_id, mc.value, a.unanswered_factor, a.high_unanswered_factor, a.wrong_factor, a.high_wrong_factor
    into alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor
    from matching.algorithm a
             join public.matching_criteriaweight mc
                  on a.location_weight_id = mc.id
    where a.active;

    -- Insert new values
    insert into matching.response_score (company_id, supporter_id, score, max_score)
    select vw.company_id, vw.supporter_id, vw.score, vw.max_score
    from matching.get_responses(alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor) as vw
    where (_refresh_all OR vw.company_id = _company_id OR vw.supporter_id = _supporter_id);
end;
$$;


-- alter totals calculation

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
        where company_id = _company_id or supporter_id = _supporter_id;
    end if;

    -- Process new total scores
    insert into matching.total_score
    select *
    from matching.active_total_scores_view as t
    where (_refresh_all or t.company_id = _company_id or t.supporter_id = _supporter_id);
end;
$$;


-- get global totals materialized

create or replace function matching.get_total_score(_algorithm_name varchar default '')
    returns TABLE(company_id integer, supporter_id integer, max_score_percentil integer, algorithm_name varchar)
    language plpgsql
as
$$
declare
    rec record;
begin
    -- Get algorithm settings
    FOR rec in
        select
            a.level_weight_id,
            mc.value as level_score,
            a.location_weight_id,
            mc1.value as location_score,
            a.sector_weight_id,
            mc2.value as sector_score,
            a.response_weight_id,
            mc3.value as response_score,
            a.high_wrong_factor,
            a.wrong_factor,
            a.high_unanswered_factor,
            a.unanswered_factor,
            a.name as algorithm_name
        from matching.algorithm a
                 join public.matching_criteriaweight mc
                      on a.level_weight_id = mc.id
                 join public.matching_criteriaweight mc1
                      on a.location_weight_id = mc1.id
                 join public.matching_criteriaweight mc2
                      on a.sector_weight_id = mc2.id
                 join public.matching_criteriaweight mc3
                      on a.response_weight_id = mc3.id
        where _algorithm_name = '' or _algorithm_name = a.name
        loop
            return query
                with scores as (
                    select *
                    from matching.get_levels(rec.level_weight_id, rec.level_score, rec.unanswered_factor, rec.high_unanswered_factor, rec.wrong_factor , rec.high_wrong_factor)
                    union all
                    select *
                    from matching.get_locations(rec.location_weight_id, rec.location_score, rec.unanswered_factor, rec.high_unanswered_factor, rec.wrong_factor , rec.high_wrong_factor)
                    union all
                    select *
                    from matching.get_sectors(rec.sector_weight_id, rec.sector_score, rec.unanswered_factor, rec.high_unanswered_factor, rec.wrong_factor , rec.high_wrong_factor)
                    union all
                    select *
                    from matching.get_responses(rec.response_weight_id, rec.response_score, rec.unanswered_factor, rec.high_unanswered_factor, rec.wrong_factor , rec.high_wrong_factor)
                )

                select distinct
                    l.company_id,
                    l.supporter_id,
                    round(l.score * 100 / l.max_score, 0)::integer as max_score_percentil,
                    rec.algorithm_name
                from (
                         select s.company_id                as company_id,
                                s.supporter_id              as supporter_id,
                                sum(s.score::integer)       as score,
                                sum(s.max_score::integer)   as max_score
                         from scores s
                         group by s.company_id, s.supporter_id) as l
                where l.score > 0;
        end loop;
end ;
$$;

create materialized view matching.global_total_score as
select *
from matching.get_total_score();

-- update existing materialized views

drop view if exists matching.exclusion_match_quantity_view;
drop materialized view if exists matching.exclusion_total_score;
create materialized view matching.exclusion_total_score as
SELECT
    company_id,
    supporter_id,
    max_score_percentil
FROM matching.get_total_score('exclusion@1.0.0');
create view matching.exclusion_match_quantity_view(company_id, type, match_quantity) as
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

drop view if exists matching.initial_match_quantity_view;
drop materialized view if exists matching.initial_total_score;
create materialized view matching.initial_total_score as
SELECT
    company_id,
    supporter_id,
    max_score_percentil
FROM matching.get_total_score('initial@1.0.0');
create view matching.initial_match_quantity_view(company_id, type, match_quantity) as
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

drop view if exists matching.penalisation_match_quantity_view;
drop materialized view if exists matching.penalisation_total_score;
create materialized view matching.penalisation_total_score as
SELECT
    company_id,
    supporter_id,
    max_score_percentil
FROM matching.get_total_score('penalisation@1.0.0');
create view matching.penalisation_match_quantity_view(company_id, type, match_quantity) as
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

create materialized view matching.penalisation101_total_score as
SELECT
    company_id,
    supporter_id,
    max_score_percentil
FROM matching.get_total_score('penalisation@1.0.1');
create view matching.penalisation101_match_quantity_view(company_id, type, match_quantity) as
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
               LEFT JOIN matching.penalisation101_total_score s ON s.supporter_id = ms.id
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
               LEFT JOIN matching.penalisation101_total_score s ON s.company_id = vc.id
      WHERE vc.type = 0
      GROUP BY vc.id, vc.type) mq
ORDER BY mq.company_id;


-- remove dispensable methods

drop function if exists matching.get_initial_levels(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_exclusion_levels(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_penalisation_levels(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_initial_locations(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_exclusion_locations(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_penalisation_locations(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_initial_sectors(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_exclusion_sectors(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_penalisation_sectors(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_initial_responses(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_exclusion_responses(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_penalisation_responses(alg_weight_id integer, alg_score integer);
drop function if exists matching.get_initial_total_score();
drop function if exists matching.get_exclusion_total_score();
drop function if exists matching.get_penalisation_total_score();

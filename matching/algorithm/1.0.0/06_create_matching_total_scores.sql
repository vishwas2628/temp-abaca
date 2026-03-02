create schema if not exists matching;

-- Create total scores table

drop table if exists matching.total_score cascade;
create table matching.total_score
(
    company_id          integer,
    supporter_id        integer,
    score               integer,
    max_score           integer,
    max_score_percentil integer,
    created_at          timestamp without time zone default now(),
    primary key (company_id, supporter_id, created_at)
);


-- Create active total scores view

drop view if exists matching.active_total_scores_view;
create or replace view matching.active_total_scores_view as
(
with scores as (
    select *
    from matching.location_score
    union all
    select *
    from matching.level_score
    union all
    select *
    from matching.sector_score
    union all
    select *
    from matching.response_score
)

select distinct l.*,
                round(l.score * 100 / l.max_score, 0) as max_score_percentil
from (
         select esv.company_id            as company_id,
                esv.supporter_id          as supporter_id,
                sum(s.score::integer)     as score,
                sum(s.max_score::integer) as max_score
         from matching.entrepreneur_supporter_view esv
                  join scores s
                       on s.company_id = esv.company_id and
                          s.supporter_id = esv.supporter_id
         group by esv.company_id, esv.supporter_id) as l
where l.score > 0
    );


-- Create trigger to recalculate total score

drop function if exists matching.refresh_total_score(_refresh_all bool, _company_id integer, _supporter_id integer);
create or replace function matching.refresh_total_score(_refresh_all bool default true,
                                                        _company_id integer default -1,
                                                        _supporter_id integer default -1)
    returns void
as
$$
begin
    -- Remove old scores
    delete
    from matching.total_score t
    where (_refresh_all or t.company_id = _company_id or t.supporter_id = _supporter_id);

    -- Process new total scores
    insert into matching.total_score
    select *
    from matching.active_total_scores_view as t
    where (_refresh_all or t.company_id = _company_id or t.supporter_id = _supporter_id);
end;
$$
    language plpgsql;


-- Create function to fetch total scores on initial algorithm, and add it to a materialized view

drop function if exists matching.get_initial_total_score();
create or replace function matching.get_initial_total_score()
    returns table
            (
                company_id          integer,
                supporter_id        integer,
                max_score_percentil integer
            )
as
$$
declare
    alg_level_weight_id    integer;
    alg_level_score        integer;
    alg_location_weight_id integer;
    alg_location_score     integer;
    alg_sector_weight_id   integer;
    alg_sector_score       integer;
    alg_response_weight_id integer;
    alg_response_score     integer;
begin
    -- Get algorithm settings
    select a.level_weight_id,
           mc.value,
           a.location_weight_id,
           mc1.value,
           a.sector_weight_id,
           mc2.value,
           a.response_weight_id,
           mc3.value
    into alg_level_weight_id,
        alg_level_score,
        alg_location_weight_id,
        alg_location_score ,
        alg_sector_weight_id ,
        alg_sector_score ,
        alg_response_weight_id,
        alg_response_score
    from matching.algorithm a
             join matching_criteriaweight mc
                  on a.level_weight_id = mc.id
             join matching_criteriaweight mc1
                  on a.location_weight_id = mc1.id
             join matching_criteriaweight mc2
                  on a.sector_weight_id = mc2.id
             join matching_criteriaweight mc3
                  on a.response_weight_id = mc3.id
    where a.prefix = 'initial';


    return query
        with scores as (
            select *
            from matching.get_initial_levels(alg_level_weight_id, alg_level_score)
            union all
            select *
            from matching.get_initial_locations(alg_location_weight_id, alg_location_score)
            union all
            select *
            from matching.get_initial_sectors(alg_sector_weight_id, alg_sector_score)
            union all
            select *
            from matching.get_initial_responses(alg_response_weight_id, alg_response_score)
        )

        select distinct l.company_id,
                        l.supporter_id,
                        round(l.score * 100 / l.max_score, 0)::integer as max_score_percentil
        from (
                 select esv.company_id            as company_id,
                        esv.supporter_id          as supporter_id,
                        sum(s.score::integer)     as score,
                        sum(s.max_score::integer) as max_score
                 from matching.entrepreneur_supporter_view esv
                          join scores s
                               on s.company_id = esv.company_id and
                                  s.supporter_id = esv.supporter_id
                 group by esv.company_id, esv.supporter_id) as l
        where l.score > 0;
end ;
$$
    language plpgsql;
drop materialized view if exists matching.initial_total_score;
create materialized view matching.initial_total_score as
select *
from matching.get_initial_total_score();


-- Create function to fetch total scores on exclusion algorithm, and add it to a materialized view

drop function if exists matching.get_exclusion_total_score();
create or replace function matching.get_exclusion_total_score()
    returns table
            (
                company_id          integer,
                supporter_id        integer,
                max_score_percentil integer
            )
as
$$
declare
    alg_level_weight_id    integer;
    alg_level_score        integer;
    alg_location_weight_id integer;
    alg_location_score     integer;
    alg_sector_weight_id   integer;
    alg_sector_score       integer;
    alg_response_weight_id integer;
    alg_response_score     integer;
begin
    -- Get algorithm settings
    select a.level_weight_id,
           mc.value,
           a.location_weight_id,
           mc1.value,
           a.sector_weight_id,
           mc2.value,
           a.response_weight_id,
           mc3.value
    into alg_level_weight_id,
        alg_level_score,
        alg_location_weight_id,
        alg_location_score ,
        alg_sector_weight_id ,
        alg_sector_score ,
        alg_response_weight_id,
        alg_response_score
    from matching.algorithm a
             join matching_criteriaweight mc
                  on a.level_weight_id = mc.id
             join matching_criteriaweight mc1
                  on a.location_weight_id = mc1.id
             join matching_criteriaweight mc2
                  on a.sector_weight_id = mc2.id
             join matching_criteriaweight mc3
                  on a.response_weight_id = mc3.id
    where a.prefix = 'exclusion';

    return query
        with scores as (
            select *
            from matching.get_exclusion_levels(alg_level_weight_id, alg_level_score)
            union all
            select *
            from matching.get_exclusion_locations(alg_location_weight_id, alg_location_score)
            union all
            select *
            from matching.get_exclusion_sectors(alg_sector_weight_id, alg_sector_score)
            union all
            select *
            from matching.get_exclusion_responses(alg_response_weight_id, alg_response_score)
        )

        select distinct l.company_id,
                        l.supporter_id,
                        round(l.score * 100 / l.max_score, 0)::integer as max_score_percentil
        from (
                 select esv.company_id            as company_id,
                        esv.supporter_id          as supporter_id,
                        sum(s.score::integer)     as score,
                        sum(s.max_score::integer) as max_score
                 from matching.entrepreneur_supporter_view esv
                          join scores s
                               on s.company_id = esv.company_id and
                                  s.supporter_id = esv.supporter_id
                 group by esv.company_id, esv.supporter_id) as l
        where l.score > 0;
end ;
$$
    language plpgsql;
drop materialized view if exists matching.exclusion_total_score;
create materialized view matching.exclusion_total_score as
select *
from matching.get_exclusion_total_score();

-- Create function to fetch total scores on penalisation algorithm, and add it to a materialized view

drop function if exists matching.get_penalisation_total_score();
create or replace function matching.get_penalisation_total_score()
    returns table
            (
                company_id          integer,
                supporter_id        integer,
                max_score_percentil integer
            )
as
$$
declare
    alg_level_weight_id    integer;
    alg_level_score        integer;
    alg_location_weight_id integer;
    alg_location_score     integer;
    alg_sector_weight_id   integer;
    alg_sector_score       integer;
    alg_response_weight_id integer;
    alg_response_score     integer;
begin
    -- Get algorithm settings
    select a.level_weight_id,
           mc.value,
           a.location_weight_id,
           mc1.value,
           a.sector_weight_id,
           mc2.value,
           a.response_weight_id,
           mc3.value
    into alg_level_weight_id,
        alg_level_score,
        alg_location_weight_id,
        alg_location_score ,
        alg_sector_weight_id ,
        alg_sector_score ,
        alg_response_weight_id,
        alg_response_score
    from matching.algorithm a
             join matching_criteriaweight mc
                  on a.level_weight_id = mc.id
             join matching_criteriaweight mc1
                  on a.location_weight_id = mc1.id
             join matching_criteriaweight mc2
                  on a.sector_weight_id = mc2.id
             join matching_criteriaweight mc3
                  on a.response_weight_id = mc3.id
    where a.prefix = 'penalisation';


    return query
        with scores as (
            select *
            from matching.get_penalisation_levels(alg_level_weight_id, alg_level_score)
            union all
            select *
            from matching.get_penalisation_locations(alg_location_weight_id, alg_location_score)
            union all
            select *
            from matching.get_penalisation_sectors(alg_sector_weight_id, alg_sector_score)
            union all
            select *
            from matching.get_penalisation_responses(alg_response_weight_id, alg_response_score)
        )

        select distinct l.company_id,
                        l.supporter_id,
                        round(l.score * 100 / l.max_score, 0)::integer as max_score_percentil
        from (
                 select esv.company_id            as company_id,
                        esv.supporter_id          as supporter_id,
                        sum(s.score::integer)     as score,
                        sum(s.max_score::integer) as max_score
                 from matching.entrepreneur_supporter_view esv
                          join scores s
                               on s.company_id = esv.company_id and
                                  s.supporter_id = esv.supporter_id
                 group by esv.company_id, esv.supporter_id) as l
        where l.score > 0;
end ;
$$
    language plpgsql;
drop materialized view if exists matching.penalisation_total_score;
create materialized view matching.penalisation_total_score as
select *
from matching.get_penalisation_total_score();

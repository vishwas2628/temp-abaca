create schema if not exists matching;

-- Create level score table

drop table if exists matching.level_score cascade;
create table matching.level_score
(
    company_id   integer,
    supporter_id integer,
    score        integer,
    max_score    integer,
    created_at   timestamp without time zone default now(),
    primary key (company_id, supporter_id, created_at)
);


-- Create view for latest assessment per entrepreneur

drop view if exists matching.latest_assessments_view cascade;
create or replace view matching.latest_assessments_view as
(
select company_id,
       company_level
from (
         select ga.evaluated                                                 as company_id,
                gl.value                                                     as company_level,
                row_number()
                over (partition by ga.evaluated order by ga.created_at desc) as entry_number
         from grid_assessment ga
                  join grid_level gl on gl.id = ga.level_id) as latest
where entry_number = 1
    );


-- Create view for assessment match view

drop view if exists matching.match_assessment_view;
create or replace view matching.match_assessment_view as
(
select esv.company_id                                                    as company_id,
       esv.supporter_id                                                  as supporter_id,
       esv.level_weight_id                                               as weight_id,
       esv.level_score                                                   as default_score,
       (la.company_level = lower(esv.supporter_level_range)
           or (la.company_level >= lower(esv.supporter_level_range)
               and la.company_level < upper(esv.supporter_level_range))) as is_match
from matching.entrepreneur_supporter_view as esv
         join matching.latest_assessments_view as la
              on la.company_id = esv.company_id
    );


-- Create function to fetch levels on initial algorithm

drop function if exists matching.get_initial_levels(alg_weight_id integer, alg_score integer);
create or replace function matching.get_initial_levels(alg_weight_id integer,
                                                       alg_score integer)
    returns table
            (
                company_id   integer,
                supporter_id integer,
                score        integer,
                max_score    integer
            )
as
$$
begin
    return query
        select l.company_id,
               l.supporter_id,
               l.score,
               l.max_score
        from (
                 select am.*,
                        (case
                             when am.is_match
                                 then coalesce(am.default_score, alg_score)
                             else 0
                            end)                              as score,
                        coalesce(am.default_score, alg_score) as max_score
                 from matching.match_assessment_view am) as l;
end;
$$
    language plpgsql;


-- Create function to fetch levels on exclusion algorithm

drop function if exists matching.get_exclusion_levels(alg_weight_id integer, alg_score integer);
create or replace function matching.get_exclusion_levels(alg_weight_id integer,
                                                         alg_score integer)
    returns table
            (
                company_id   integer,
                supporter_id integer,
                score        integer,
                max_score    integer
            )
as
$$
begin
    return query
        select l.company_id,
               l.supporter_id,
               l.score,
               l.max_score
        from (
                 select am.*,
                        (case
                             when am.is_match
                                 then coalesce(am.default_score, alg_score)
                             when coalesce(am.weight_id, alg_weight_id) = 5
                                 then -coalesce(am.default_score, alg_score) * 1000
                             else -coalesce(am.default_score, alg_score)
                            end)                              as score,
                        coalesce(am.default_score, alg_score) as max_score
                 from matching.match_assessment_view am) as l;
end;
$$
    language plpgsql;


-- Create function to fetch levels on penalisation algorithm

drop function if exists matching.get_penalisation_levels(alg_weight_id integer, alg_score integer);
create or replace function matching.get_penalisation_levels(alg_weight_id integer,
                                                            alg_score integer)
    returns table
            (
                company_id   integer,
                supporter_id integer,
                score        integer,
                max_score    integer
            )
as
$$
begin
    return query
        select l.company_id,
               l.supporter_id,
               l.score,
               l.max_score
        from (
                 select am.*,
                        (case
                             when am.is_match
                                 then coalesce(am.default_score, alg_score)
                             when coalesce(am.weight_id, alg_weight_id) = 5
                                 then -coalesce(am.default_score, alg_score) / 2
                             else 0
                            end)                              as score,
                        coalesce(am.default_score, alg_score) as max_score
                 from matching.match_assessment_view am) as l;
end;
$$
    language plpgsql;


-- Create trigger to recalculate level score

drop function if exists matching.refresh_level_score(_refresh_all boolean, _company_id integer, _supporter_id integer);
create or replace function matching.refresh_level_score(_refresh_all bool default true,
                                                        _company_id integer default -1,
                                                        _supporter_id integer default -1)
    returns void
as
$$
declare
    alg_prefix    varchar;
    alg_weight_id integer;
    alg_score     integer;
begin
    -- Get active algorithm settings
    select a.prefix,
           a.level_weight_id,
           mc.value
    into alg_prefix, alg_weight_id, alg_score
    from matching.algorithm a
             join matching_criteriaweight mc
                  on a.level_weight_id = mc.id
    where a.active;

    if alg_prefix is not null and alg_weight_id is not null and alg_score is not null then
        -- Remove old scores
        delete
        from matching.level_score
        where (_refresh_all or company_id = _company_id or supporter_id = _supporter_id);

        -- Insert new values
        execute format('insert into matching.level_score (company_id, supporter_id, score, max_score)' ||
                       'select * from matching.get_%s_levels(%s, %s)' ||
                       'as vw where ($1 OR vw.company_id = $2 OR vw.supporter_id = $3)', alg_prefix, alg_weight_id,
                       alg_score)
            using _refresh_all, _company_id, _supporter_id;
    end if;
end;
$$
    language plpgsql;

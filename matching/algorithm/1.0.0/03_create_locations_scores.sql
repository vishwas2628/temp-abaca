create schema if not exists matching;

-- Create location scores table

drop table if exists matching.location_score cascade;
create table matching.location_score
(
    company_id   integer,
    supporter_id integer,
    score        integer,
    max_score    integer,
    created_at   timestamp without time zone default now(),
    primary key (company_id, supporter_id, created_at)
);


-- Create view for matching locations

drop view if exists matching.match_location_view;
create or replace view matching.match_location_view as
(
select distinct esv.company_id             as company_id,
       esv.supporter_id           as supporter_id,
       esv.location_weight_id     as weight_id,
       esv.location_score         as default_score,
       esl.company_id is not null as is_match
from matching.entrepreneur_supporter_view as esv
         left outer join (
    select cl.company_id   as company_id,
           sl.supporter_id as supporter_id
    from (
             select vcl.company_id,
                    vl.continent,
                    vl.country,
                    vl.city,
                    vl.region
             from viral_company_locations vcl
                      join viral_location vl
                           on vcl.location_id = vl.id) as cl
             join (
        select msl.supporter_id,
               vl.continent,
               vl.country,
               vl.city,
               vl.region
        from matching_supporter_locations msl
                 join viral_location vl
                      on msl.location_id = vl.id) as sl
                  on sl.country = cl.country
                      and (sl.continent = cl.continent or
                           sl.continent = '')
                      and (sl.city = cl.city or sl.city = '')
                      and (sl.region = cl.region or sl.region = '')) as esl
                         on esl.company_id = esv.company_id and esl.supporter_id = esv.supporter_id
    );

select *
    from matching.match_location_view;


-- Create function to fetch locations on initial algorithm

drop function if exists matching.get_initial_locations(alg_weight_id integer, alg_score integer);
create or replace function matching.get_initial_locations(alg_weight_id integer,
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
                 from matching.match_location_view am) as l;
end;
$$
    language plpgsql;


-- Create function to fetch locations on exclusion algorithm

drop function if exists matching.get_exclusion_locations(alg_weight_id integer, alg_score integer);
create or replace function matching.get_exclusion_locations(alg_weight_id integer,
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
                 from matching.match_location_view am) as l;
end;
$$
    language plpgsql;


-- Create function to fetch locations on penalisation algorithm

drop function if exists matching.get_penalisation_locations(alg_weight_id integer, alg_score integer);
create or replace function matching.get_penalisation_locations(alg_weight_id integer,
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
                 from matching.match_location_view am) as l;
end;
$$
    language plpgsql;


-- Create trigger to recalculate location score

drop function if exists matching.refresh_location_score(_refresh_all bool, _company_id integer, _supporter_id integer);
create or replace function matching.refresh_location_score(_refresh_all bool default true,
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
           a.location_weight_id,
           mc.value
    into alg_prefix, alg_weight_id, alg_score
    from matching.algorithm a
             join matching_criteriaweight mc
                  on a.location_weight_id = mc.id
    where a.active;

    if alg_prefix is not null and alg_weight_id is not null and alg_score is not null then
        -- Remove old scores
        delete
        from matching.location_score
        where (_refresh_all or company_id = _company_id or supporter_id = _supporter_id);

        -- Insert new values
        execute format('insert into matching.location_score (company_id, supporter_id, score, max_score) ' ||
                       'select * from matching.get_%s_locations(%s, %s) as vw ' ||
                       'where ($1 OR vw.company_id = $2 OR vw.supporter_id = $3)', alg_prefix, alg_weight_id,
                       alg_score)
            using _refresh_all, _company_id, _supporter_id;
    end if;
end;
$$
    language plpgsql;

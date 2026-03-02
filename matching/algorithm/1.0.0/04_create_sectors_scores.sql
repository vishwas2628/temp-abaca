create schema if not exists matching;

-- Create sector scores table

drop table if exists matching.sector_score cascade;
create table matching.sector_score
(
    company_id   integer,
    supporter_id integer,
    score        integer,
    max_score    integer,
    created_at   timestamp without time zone default now(),
    primary key (company_id, supporter_id, created_at)
);


-- Create view for sectors match view

drop view if exists matching.match_sector_view;
create or replace view matching.match_sector_view as
(
select esv.company_id                                           as company_id,
       esv.supporter_id                                         as supporter_id,
       esv.sector_weight_id                                     as weight_id,
       esv.sector_score                                         as default_score,
       -- Check if Supporter does not have sectors
       (not exists(
               select id
               from matching_supporter_sectors
               where supporter_id = esv.supporter_id)
           or
           -- Check if there's a match between Entrepreneur and Supporter sectors
        exists(
                select id
                from viral_company_sectors
                where company_id = esv.company_id
                  and sector_id in
                      (select sector_id
                       from matching_supporter_sectors
                       where supporter_id = esv.supporter_id))) as is_match
from matching.entrepreneur_supporter_view as esv
    );


-- Create function to fetch sectors on initial algorithm

drop function if exists matching.get_initial_sectors(alg_weight_id integer, alg_score integer);
create or replace function matching.get_initial_sectors(alg_weight_id integer,
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
                 from matching.match_sector_view am) as l;
end;
$$
    language plpgsql;


-- Create function to fetch sectors on exclusion algorithm

drop function if exists matching.get_exclusion_sectors(alg_weight_id integer, alg_score integer);
create or replace function matching.get_exclusion_sectors(alg_weight_id integer,
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
                 from matching.match_sector_view am) as l;
end;
$$
    language plpgsql;


-- Create function to fetch sectors on penalisation algorithm

drop function if exists matching.get_penalisation_sectors(alg_weight_id integer, alg_score integer);
create or replace function matching.get_penalisation_sectors(alg_weight_id integer,
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
                 from matching.match_sector_view am) as l;
end;
$$
    language plpgsql;


-- Create trigger to recalculate sector score

drop function if exists matching.refresh_sector_score(_refresh_all boolean, _company_id integer, _supporter_id integer);
create or replace function matching.refresh_sector_score(_refresh_all bool default true,
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
           a.sector_weight_id,
           mc.value
    into alg_prefix, alg_weight_id, alg_score
    from matching.algorithm a
             join matching_criteriaweight mc
                  on a.sector_weight_id = mc.id
    where a.active;

    if alg_prefix is not null and alg_weight_id is not null and alg_score is not null then
        -- Remove old scores
        delete
        from matching.sector_score
        where (_refresh_all or company_id = _company_id or supporter_id = _supporter_id);

        -- Insert new values
        execute format('insert into matching.sector_score (company_id, supporter_id, score, max_score)' ||
                       'select * from matching.get_%s_sectors(%s, %s)' ||
                       'as vw where ($1 OR vw.company_id = $2 OR vw.supporter_id = $3)', alg_prefix, alg_weight_id,
                       alg_score)
            using _refresh_all, _company_id, _supporter_id;
    end if;
end;
$$
    language plpgsql;

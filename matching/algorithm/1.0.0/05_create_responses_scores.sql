create schema if not exists matching;

-- Create question responses scores table

drop table if exists matching.response_score cascade;
create table matching.response_score
(
    company_id   integer,
    supporter_id integer,
    score        integer,
    max_score    integer,
    created_at   timestamp without time zone default now(),
    primary key (company_id, supporter_id, created_at)
);


-- Create view for matching criteria per question

drop view if exists matching.question_criteria_view cascade;
create or replace view matching.question_criteria_view as
(
select mc.id           as criteria_id,
       mc.supporter_id as supporter_id,
       mc.question_id  as question_id,
       mqt.type        as question_type,
       mcw.id          as criteriaweight_id,
       mcw.value       as score,
       mc.desired      as desired_answers,
       (
           select jsonb_agg(answer_id)
           from matching_criteria_answers
           where mc.id = criteria_id
           group by criteria_id
       )               as desired_selected_answers
from matching_criteria mc
         join matching_question mq on mq.id = mc.question_id
         join matching_questiontype mqt on mq.question_type_id = mqt.id
         left outer join matching_criteriaweight mcw on mc.criteria_weight_id = mcw.id
    );


-- Create view for matching responses correctness validation

drop view if exists matching.match_response_view;
create or replace view matching.match_response_view as
(
select *
from (
         select vu.company_id                                                                                  as company_id,
                qc.supporter_id                                                                                as supporter_id,
                ( -- Single and multiple select question responses validations
                        ((qc.question_type = 'single-select' or
                          qc.question_type = 'multi-select')
                            and exists(
                                 select 1
                                 from matching_response_answers
                                 where matching_response_answers.response_id = mr.id
                                   and matching_response_answers.answer_id::text in (select value
                                                                                     from jsonb_array_elements_text(
                                                                                             qc.desired_selected_answers))))
                        -- Numeric question responses validations
                        or (qc.question_type = 'numeric'
                        and ((qc.desired_answers ?| array ['max', 'min']
                            and qc.desired_answers ->> 'max' >=
                                mr.value ->> 'value'
                            and qc.desired_answers ->> 'min' <=
                                mr.value ->> 'value')
                            or (qc.desired_answers ? 'max' and
                                qc.desired_answers ->> 'max' >=
                                mr.value ->> 'value')
                            or (qc.desired_answers ? 'min' and
                                qc.desired_answers ->> 'min' <=
                                mr.value ->> 'value')))
                        -- Range question responses validations
                        or (qc.question_type = 'range'
                        and ((mr.value ?| array ['max', 'min']
                            and mr.value ->> 'max' >=
                                qc.desired_answers ->> 'value'
                            and mr.value ->> 'min' <=
                                qc.desired_answers ->> 'value')
                            or (mr.value ? 'max' and
                                mr.value ->> 'max' >=
                                qc.desired_answers ->> 'value')
                            or (mr.value ? 'min' and
                                mr.value ->> 'min' <=
                                qc.desired_answers ->> 'value')))
                    )                                                                                          as is_correct,
                qc.score                                                                                       as default_score,
                qc.criteriaweight_id                                                                           as weight_id,
                -- Order by response date
                row_number()
                over (partition by vu.company_id, qc.supporter_id, mr.question_id order by mr.created_at desc) as response_number
         from matching.question_criteria_view qc
                  left outer join matching_response mr
                                  on mr.question_id = qc.question_id
                  join viral_userprofile vu on mr.user_profile_id = vu.id
     ) q
where q.response_number = 1);


-- Create function to fetch responses on initial algorithm

drop function if exists matching.get_initial_responses(alg_weight_id integer, alg_score integer);
create or replace function matching.get_initial_responses(alg_weight_id integer,
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
        select esv.company_id    as company_id,
               esv.supporter_id  as supporter_id,
               sum(case
                       when am.is_correct
                           then coalesce(am.default_score, alg_score)
                       else
                           0
                   end)::integer as score,
               q.max_score       as max_score
        from matching.entrepreneur_supporter_view esv
                 join (
            select qc.supporter_id,
                   sum(coalesce(qc.score, alg_score))::integer as max_score
            from matching.question_criteria_view qc
            group by qc.supporter_id) q on q.supporter_id = esv.supporter_id
                 left outer join matching.match_response_view am
                                 on am.supporter_id = esv.supporter_id and am.company_id = esv.company_id
        group by esv.company_id, esv.supporter_id, q.max_score;
end;
$$
    language plpgsql;


-- Create function to fetch responses on exclusion algorithm

drop function if exists matching.get_exclusion_responses(alg_weight_id integer, alg_score integer);
create or replace function matching.get_exclusion_responses(alg_weight_id integer,
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
        select esv.company_id    as company_id,
               esv.supporter_id  as supporter_id,
               sum(case
                       when am.is_correct
                           then coalesce(am.default_score, alg_score)
                       when coalesce(am.weight_id, alg_weight_id) = 5
                           then -coalesce(am.default_score, alg_score) * 1000
                       else -coalesce(am.default_score, alg_score)
                   end)::integer as score,
               q.max_score       as max_score
        from matching.entrepreneur_supporter_view esv
                 join (
            select qc.supporter_id,
                   sum(coalesce(qc.score, alg_score))::integer as max_score
            from matching.question_criteria_view qc
            group by qc.supporter_id) q on q.supporter_id = esv.supporter_id
                 left outer join matching.match_response_view am
                                 on am.supporter_id = esv.supporter_id and am.company_id = esv.company_id
        group by esv.company_id, esv.supporter_id, q.max_score;
end;
$$
    language plpgsql;


-- Create function to fetch responses on penalisation algorithm

drop function if exists matching.get_penalisation_responses(alg_weight_id integer, alg_score integer);
create or replace function matching.get_penalisation_responses(alg_weight_id integer,
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
        select esv.company_id    as company_id,
               esv.supporter_id  as supporter_id,
               sum(case
                       when am.is_correct
                           then coalesce(am.default_score, alg_score)
                       when coalesce(am.weight_id, alg_weight_id) = 5
                           then -coalesce(am.default_score, alg_score) / 2
                       else 0
                   end)::integer as score,
               q.max_score       as max_score
        from matching.entrepreneur_supporter_view esv
                 join (
            select qc.supporter_id,
                   sum(coalesce(qc.score, alg_score))::integer as max_score
            from matching.question_criteria_view qc
            group by qc.supporter_id) q on q.supporter_id = esv.supporter_id
                 left outer join matching.match_response_view am
                                 on am.supporter_id = esv.supporter_id and am.company_id = esv.company_id
        group by esv.company_id, esv.supporter_id, q.max_score;
end;
$$
    language plpgsql;


-- Create trigger to recalculate responses score

drop function if exists matching.refresh_response_score(_refresh_all boolean, _company_id integer, _supporter_id integer);
create or replace function matching.refresh_response_score(_refresh_all bool default true,
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
           a.response_weight_id,
           mc.value
    into alg_prefix, alg_weight_id, alg_score
    from matching.algorithm a
             join matching_criteriaweight mc
                  on a.response_weight_id = mc.id
    where a.active;

    if alg_prefix is not null and alg_weight_id is not null and alg_score is not null then
        -- Remove old scores
        delete
        from matching.response_score
        where (_refresh_all or company_id = _company_id or supporter_id = _supporter_id);

        -- Insert new values
        execute format('insert into matching.response_score (company_id, supporter_id, score, max_score)' ||
                       'select * from matching.get_%s_responses(%s, %s)' ||
                       'as vw where ($1 OR vw.company_id = $2 OR vw.supporter_id = $3)', alg_prefix, alg_weight_id,
                       alg_score)
            using _refresh_all, _company_id, _supporter_id;
    end if;
end;
$$
    language plpgsql;


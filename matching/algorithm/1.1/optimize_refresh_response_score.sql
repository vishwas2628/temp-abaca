/*
  get_responses:
  - Filter entrepreneur_supporter_view with company_id and supporter_id 
*/
drop function if exists matching.get_responses(alg_weight_id integer, alg_score integer, unanswered_factor float, high_unanswered_factor float, wrong_factor float, high_wrong_factor float);

create or replace function matching.get_responses(alg_weight_id integer, alg_score integer, unanswered_factor float, high_unanswered_factor float, wrong_factor float, high_wrong_factor float, _company_id integer DEFAULT '-1'::integer, _supporter_id integer DEFAULT '-1'::integer)
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
        where (_company_id = -1 and _supporter_id = -1)
           or (_company_id > -1 and _supporter_id > -1
                  and esv.company_id = _company_id and esv.supporter_id = _supporter_id) 
           or (_supporter_id = -1 and esv.company_id = _company_id)
           or (_company_id = -1 and esv.supporter_id = _supporter_id)
        group by esv.company_id, esv.supporter_id) l;
end;
$$;


/*
  refresh_response_score:
  - Call get_responses with company_id and supporter_id 
*/
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
        where _company_id > -1 and company_id = _company_id
        or _supporter_id > -1 and supporter_id = _supporter_id;
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
    from matching.get_responses(alg_weight_id, alg_score, unanswered_factor, high_unanswered_factor, wrong_factor, high_wrong_factor, _company_id, _supporter_id) as vw;
end;
$$;
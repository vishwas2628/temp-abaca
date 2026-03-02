create schema if not exists matching;

-- Update to return question_id value
drop view if exists matching.match_response_view;
create or replace view matching.match_response_view
            (company_id, supporter_id, question_id, is_correct, default_score, weight_id, response_number)
as
(
SELECT q.company_id,
       q.supporter_id,
       q.question_id,
       q.is_correct,
       q.default_score,
       q.weight_id,
       q.response_number
FROM (SELECT vu.company_id,
             qc.supporter_id,
             qc.question_id,
             (qc.question_type::text = 'single-select'::text OR qc.question_type::text = 'multi-select'::text) AND
             (EXISTS(SELECT 1
                     FROM public.matching_response_answers mra
                     WHERE mra.response_id = mr.id
                       AND (mra.answer_id::text IN (
                           SELECT jsonb_array_elements_text.value FROM jsonb_array_elements_text(qc.desired_selected_answers) jsonb_array_elements_text(value))))) OR
             qc.question_type::text = 'numeric'::text AND (qc.desired_answers ?| ARRAY ['max'::text, 'min'::text] AND
                                                           (qc.desired_answers ->> 'max'::text) >= (mr.value ->> 'value'::text) AND
                                                           (qc.desired_answers ->> 'min'::text) <= (mr.value ->> 'value'::text) OR
                                                           qc.desired_answers ? 'max'::text AND
                                                           (qc.desired_answers ->> 'max'::text) >= (mr.value ->> 'value'::text) OR
                                                           qc.desired_answers ? 'min'::text AND
                                                           (qc.desired_answers ->> 'min'::text) <= (mr.value ->> 'value'::text)) OR
             qc.question_type::text = 'range'::text AND (mr.value ?| ARRAY ['max'::text, 'min'::text] AND
                                                         (mr.value ->> 'max'::text) >= (qc.desired_answers ->> 'value'::text) AND
                                                         (mr.value ->> 'min'::text) <= (qc.desired_answers ->> 'value'::text) OR
                                                         mr.value ? 'max'::text AND
                                                         (mr.value ->> 'max'::text) >= (qc.desired_answers ->> 'value'::text) OR
                                                         mr.value ? 'min'::text AND
                                                         (mr.value ->> 'min'::text) <= (qc.desired_answers ->> 'value'::text)) AS is_correct,
             qc.score                                                                                                          AS default_score,
             qc.criteriaweight_id                                                                                              AS weight_id,
             row_number()
             OVER (PARTITION BY vu.company_id, qc.supporter_id, mr.question_id ORDER BY mr.created_at DESC)                    AS response_number
      FROM matching.question_criteria_view qc
               LEFT JOIN public.matching_response mr ON mr.question_id = qc.question_id
               JOIN public.viral_userprofile vu ON mr.user_profile_id = vu.id) q
WHERE q.response_number = 1);

-- Update to left join by match_response_view question_id and recover values from question criteria view
create or replace function matching.get_penalisation_responses(alg_weight_id integer, alg_score integer)
    returns TABLE(company_id integer, supporter_id integer, score integer, max_score integer)
    language plpgsql
as
$$
begin
    return query
        select esv.company_id,
               esv.supporter_id,
               sum(case
                       when am.is_correct
                           then coalesce(qc.score, alg_score)
                       when coalesce(qc.criteriaweight_id, alg_weight_id) = 5
                           then -coalesce(qc.score, alg_score) / 2
                       else 0
                   end)::integer as score,
               sum(coalesce(qc.score, alg_score))::integer as max_score
        from matching.entrepreneur_supporter_view esv
                 join matching.question_criteria_view qc
                      on qc.supporter_id = esv.supporter_id
                 left join matching.match_response_view am
                           on am.supporter_id = esv.supporter_id
                               and am.company_id = esv.company_id
                               and qc.question_id = am.question_id
        group by esv.company_id, esv.supporter_id;
end;
$$;

-- Updated to return only the latest criteria by question_id and supporter_id, avoiding duplicates
create or replace view matching.question_criteria_view
            (criteria_id, supporter_id, question_id, question_type, criteriaweight_id, score, desired_answers,
             desired_selected_answers)
as
SELECT
    t.criteria_id,
    t.supporter_id,
    t.question_id,
    t.question_type,
    t.criteriaweight_id,
    t.score,
    t.desired_answers,
    t.desired_selected_answers
FROM (
         SELECT
             mc.id                                            AS criteria_id,
             mc.supporter_id,
             mc.question_id,
             mqt.type                                         AS question_type,
             mcw.id                                           AS criteriaweight_id,
             mcw.value                                        AS score,
             mc.desired                                       AS desired_answers,
             (SELECT jsonb_agg(mca.answer_id) AS jsonb_agg
              FROM public.matching_criteria_answers mca
              WHERE mc.id = mca.criteria_id
              GROUP BY mca.criteria_id) AS desired_selected_answers,
             row_number() OVER (PARTITION BY mc.supporter_id, mc.question_id ORDER BY mc.created_at DESC) AS criteria_uniqueness
         FROM public.matching_criteria mc
                  JOIN public.matching_question mq ON mq.id = mc.question_id
                  JOIN public.matching_questiontype mqt ON mq.question_type_id = mqt.id
                  LEFT JOIN public.matching_criteriaweight mcw ON mc.criteria_weight_id = mcw.id) t
where t.criteria_uniqueness = 1;

-- Also
-- Update responses for initial algorithm
create or replace function matching.get_initial_responses(alg_weight_id integer, alg_score integer)
    returns TABLE(company_id integer, supporter_id integer, score integer, max_score integer)
    language plpgsql
as
$$
begin
    return query
        select esv.company_id    as company_id,
               esv.supporter_id  as supporter_id,
               sum(case
                       when am.is_correct
                           then coalesce(qc.score, alg_score)
                       else
                           0
                   end)::integer as score,
               sum(coalesce(qc.score, alg_score))::integer as max_score
        from matching.entrepreneur_supporter_view esv
                 join matching.question_criteria_view qc
                      on qc.supporter_id = esv.supporter_id
                 left join matching.match_response_view am
                           on am.supporter_id = esv.supporter_id
                               and am.company_id = esv.company_id
                               and qc.question_id = am.question_id
        group by esv.company_id, esv.supporter_id;
end;
$$;

-- And for exclusion algorithm
create or replace function matching.get_exclusion_responses(alg_weight_id integer, alg_score integer)
    returns TABLE(company_id integer, supporter_id integer, score integer, max_score integer)
    language plpgsql
as
$$
begin
    return query
        select esv.company_id    as company_id,
               esv.supporter_id  as supporter_id,
               sum(case
                       when am.is_correct
                           then coalesce(qc.score, alg_score)
                       when coalesce(qc.criteriaweight_id, alg_weight_id) = 5
                           then -coalesce(qc.score, alg_score) * 1000
                       else -coalesce(qc.score, alg_score)
                   end)::integer as score,
               sum(coalesce(qc.score, alg_score))::integer as max_score
        from matching.entrepreneur_supporter_view esv
                 join matching.question_criteria_view qc
                      on qc.supporter_id = esv.supporter_id
                 left join matching.match_response_view am
                           on am.supporter_id = esv.supporter_id
                               and am.company_id = esv.company_id
                               and qc.question_id = am.question_id
        group by esv.company_id, esv.supporter_id;
end;
$$;
create
or replace view matching.question_criteria_view
            (criteria_id, supporter_id, question_id, question_type, criteriaweight_id, score, desired_answers,
             desired_selected_answers)
as
SELECT t.criteria_id,
       t.supporter_id,
       t.question_id,
       t.question_type,
       t.criteriaweight_id,
       t.score,
       t.desired_answers,
       t.desired_selected_answers
FROM (SELECT mc.id                      AS criteria_id,
             mc.supporter_id,
             mc.question_id,
             mqt.type                   AS question_type,
             mcw.id                     AS criteriaweight_id,
             mcw.value                  AS score,
             mc.desired                 AS desired_answers,
             (SELECT jsonb_agg(mca.answer_id) AS jsonb_agg
              FROM matching_criteria_answers mca
              WHERE mc.id = mca.criteria_id
              GROUP BY mca.criteria_id) AS desired_selected_answers
      FROM public.matching_criteria mc
               JOIN public.matching_question mq ON mq.id = mc.question_id
               JOIN public.matching_questiontype mqt ON mq.question_type_id = mqt.id
               LEFT JOIN public.matching_criteriaweight mcw ON mc.criteria_weight_id = mcw.id
      WHERE mqt.type NOT IN ('free-response', 'date')
            AND mc.is_active IS TRUE) t;

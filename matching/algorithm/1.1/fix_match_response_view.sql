/*
  Fixes applied here:

  1 - Numeric string comparision is not by the actual magnitude of the number
  but instead by its alphabetical order, which means, that the following
  comparison will always return true: SELECT '2'::text > '10'::text;
  instead we need to cast them properly: SELECT '2'::numeric > '10'::numeric;

  2 - To verify if all array keys exist in a json object we need 
  to use the following operator "?&" instead of "?|" which 
  only verifies if at least one of the keys exist.

  3 - Ensuring that when a multiple json key (min & max) validation returns true 
  and its numeric comparison returns false, we verify that following single 
  key (min / max) validations rule out all the other the keys.
*/
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
                           SELECT jsonb_array_elements_text.value FROM jsonb_array_elements_text(qc.desired_selected_answers) jsonb_array_elements_text(value))))) 
                       OR qc.question_type::text = 'numeric'::text 
                            AND (qc.desired_answers ?& ARRAY ['max'::text, 'min'::text]
                                AND (qc.desired_answers ->> 'max')::numeric >= (mr.value ->> 'value')::numeric 
                                AND (qc.desired_answers ->> 'min')::numeric <= (mr.value ->> 'value')::numeric 
                            OR qc.desired_answers ? 'max'::text 
                                AND qc.desired_answers ? 'min'::text IS FALSE 
                                AND (qc.desired_answers ->> 'max')::numeric >= (mr.value ->> 'value')::numeric 
                            OR qc.desired_answers ? 'min'::text 
                                AND qc.desired_answers ? 'max'::text IS FALSE 
                                AND (qc.desired_answers ->> 'min')::numeric <= (mr.value ->> 'value')::numeric) 
                       OR qc.question_type::text = 'range'::text 
                            AND (mr.value ?& ARRAY ['max'::text, 'min'::text] 
                                AND (mr.value ->> 'max')::numeric >= (qc.desired_answers ->> 'value')::numeric 
                                AND (mr.value ->> 'min')::numeric <= (qc.desired_answers ->> 'value')::numeric 
                            OR mr.value ? 'max'::text
                                AND mr.value ? 'min'::text IS FALSE
                                AND (mr.value ->> 'max')::numeric >= (qc.desired_answers ->> 'value')::numeric 
                            OR mr.value ? 'min'::text 
                                AND mr.value ? 'max'::text IS FALSE
                                AND (mr.value ->> 'min')::numeric <= (qc.desired_answers ->> 'value')::numeric) 
                       AS is_correct,
             qc.score                                                                                                          AS default_score,
             qc.criteriaweight_id                                                                                              AS weight_id,
             row_number()
             OVER (PARTITION BY vu.company_id, qc.supporter_id, mr.question_id ORDER BY mr.created_at DESC)                    AS response_number
      FROM matching.question_criteria_view qc
               LEFT JOIN public.matching_response mr ON mr.question_id = qc.question_id
               JOIN public.viral_userprofile vu ON mr.user_profile_id = vu.id) q
WHERE q.response_number = 1);
/*
  Previously the "upper" comparison was only checking if the company level
  was lower than the upper range level which would wrongfully rule out valid matches, for example:
  
  # With the following values:
  company_level = 3
  supporter_level_range = [1, 3]
  
  # This would return false even though the company level is in fact in the supporter level range:
  company_level < upper(supporter_level_range)
*/
create or replace view matching.match_assessment_view(company_id, supporter_id, weight_id, default_score, is_match, is_unanswered) as
select esv.company_id,
       esv.supporter_id,
       esv.level_weight_id                                        AS weight_id,
       esv.level_score                                            AS default_score,
       la.company_level = lower(esv.supporter_level_range) 
       OR la.company_level >= lower(esv.supporter_level_range) 
         AND la.company_level <= upper(esv.supporter_level_range) AS is_match,
       la.company_level is null as is_unanswered
from matching.entrepreneur_supporter_view esv
         left join matching.latest_assessments_view la ON la.company_id = esv.company_id;
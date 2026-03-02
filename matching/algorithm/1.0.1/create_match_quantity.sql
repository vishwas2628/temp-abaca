-- Match quantity view for initial algorithm
drop view if exists matching.initial_match_quantity_view;
create or replace view matching.initial_match_quantity_view
as
(
select *
from (
         -- supporters
         select vc.id                                                          as company_id,
                vc.type                                                        as type,
                sum(case when s.max_score_percentil is null then 0 else 1 end) as match_quantity
         from matching_supporter ms
                  join viral_userprofile vu on ms.user_profile_id = vu.id
                  join viral_company vc on vu.company_id = vc.id
                  left outer join matching.initial_total_score s
                                  on s.supporter_id = ms.id
         group by vc.id, vc.type
         union all
         -- entrepreneurs
         select vc.id                                                          as company_id,
                vc.type                                                        as type,
                sum(case when s.max_score_percentil is null then 0 else 1 end) as match_quantity
         from viral_company vc
                  left outer join matching.initial_total_score s
                                  on s.company_id = vc.id
         where vc.type = 0
         group by vc.id, vc.type) mq
order by mq.company_id
    );


-- Match quantity view for exclusion algorithm

drop view if exists matching.exclusion_match_quantity_view;
create or replace view matching.exclusion_match_quantity_view
as
(
select *
from (
         -- supporters
         select vc.id                                                          as company_id,
                vc.type                                                        as type,
                sum(case when s.max_score_percentil is null then 0 else 1 end) as match_quantity
         from matching_supporter ms
                  join viral_userprofile vu on ms.user_profile_id = vu.id
                  join viral_company vc on vu.company_id = vc.id
                  left outer join matching.exclusion_total_score s
                                  on s.supporter_id = ms.id
         group by vc.id, vc.type
         union all
         -- entrepreneurs
         select vc.id                                                          as company_id,
                vc.type                                                        as type,
                sum(case when s.max_score_percentil is null then 0 else 1 end) as match_quantity
         from viral_company vc
                  left outer join matching.exclusion_total_score s
                                  on s.company_id = vc.id
         where vc.type = 0
         group by vc.id, vc.type) mq
order by mq.company_id
    );


-- Match quantity view for penalisation algorithm

drop view if exists matching.penalisation_match_quantity_view;
create or replace view matching.penalisation_match_quantity_view
as
(
select *
from (
         -- supporters
         select vc.id                                                          as company_id,
                vc.type                                                        as type,
                sum(case when s.max_score_percentil is null then 0 else 1 end) as match_quantity
         from matching_supporter ms
                  join viral_userprofile vu on ms.user_profile_id = vu.id
                  join viral_company vc on vu.company_id = vc.id
                  left outer join matching.penalisation_total_score s
                                  on s.supporter_id = ms.id
         group by vc.id, vc.type
         union all
         -- entrepreneurs
         select vc.id                                                          as company_id,
                vc.type                                                        as type,
                sum(case when s.max_score_percentil is null then 0 else 1 end) as match_quantity
         from viral_company vc
                  left outer join matching.penalisation_total_score s
                                  on s.company_id = vc.id
         where vc.type = 0
         group by vc.id, vc.type) mq
order by mq.company_id);

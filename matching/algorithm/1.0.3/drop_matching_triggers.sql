-- matching_supporter on insert or update

drop trigger if exists matching_supporter_materialized_insert_update on matching_supporter cascade;
drop function if exists matching_supporter_materialized_insert_update();


-- matching_supporter_sectors on insert or delete

drop trigger if exists matching_supporter_sectors_materialized_insert_delete on matching_supporter_sectors cascade;
drop function if exists matching_supporter_sectors_materialized_insert_delete();


-- viral_company_sectors on insert or delete

drop trigger if exists viral_company_sectors_materialized_insert_delete on viral_company_sectors cascade;
drop function if exists viral_company_sectors_materialized_insert_delete();


-- matching_supporter_locations on insert or delete

drop trigger if exists matching_supporter_locations_materialized_insert_delete on matching_supporter_locations cascade;
drop function if exists matching_supporter_locations_materialized_insert_delete();


-- viral_company_locations on insert or delete

drop trigger if exists viral_company_locations_materialized_insert_delete on viral_company_locations cascade;
drop function if exists viral_company_locations_materialized_insert_delete();


-- matching_criteria on insert or update or delete

drop trigger if exists matching_criteria_materialized_insert_update_delete on matching_criteria cascade;
drop function if exists matching_criteria_materialized_insert_update_delete();


-- matching_criteria_answers on insert or delete

drop trigger if exists matching_criteria_answers_materialized_insert_delete on matching_criteria_answers cascade;
drop function if exists matching_criteria_answers_materialized_insert_delete();


-- matching_response on insert or update or delete

drop trigger if exists matching_response_materialized_insert_update_delete on matching_response cascade;
drop function if exists matching_response_materialized_insert_update_delete();


-- matching_response_answers on insert or delete

drop trigger if exists matching_response_answers_materialized_insert_delete on matching_response_answers cascade;
drop function if exists matching_response_answers_materialized_insert_delete();


-- grid_assessment on insert

drop trigger if exists grid_assessment_materialized_insert on grid_assessment cascade;
drop function if exists grid_assessment_materialized_insert();


-- viral_company on insert or delete

drop trigger if exists viral_company_materialized_insert_delete on viral_company cascade;
drop function if exists viral_company_materialized_insert_delete();

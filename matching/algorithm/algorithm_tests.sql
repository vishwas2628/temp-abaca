-- Tests

-- Update active algorithm
update matching.algorithm
set active = true
where prefix = 'initial';


-- Reports

-- Initial algorithm

refresh materialized view matching.initial_total_score;
select *
from matching.initial_total_score;


-- Exclusion algorithm

refresh materialized view matching.exclusion_total_score;
select *
from matching.exclusion_total_score;


-- Penalisation algorithm

refresh materialized view matching.penalisation_total_score;
select *
from matching.penalisation_total_score;

-- Old Nightly run
do
$$
    begin
        perform refresh_level_score();
        perform refresh_location_score();
        perform refresh_response_score();
        perform refresh_sector_score();
        perform refresh_matching_total_score();
    end;
$$;

-- New Nightly run
do
$$
    begin
        perform matching.refresh_level_score();
        perform matching.refresh_location_score();
        perform matching.refresh_response_score();
        perform matching.refresh_sector_score();
        perform matching.refresh_total_score();
    end;
$$;

-- Old totals
select *
from matview.matching_total_scores;

-- New totals
select *
from matching.total_score;
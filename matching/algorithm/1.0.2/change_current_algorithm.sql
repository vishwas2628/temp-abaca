-- Trigger for algorithm on update
drop trigger if exists algorithm_update on matching.algorithm cascade;
create or replace function matching.algorithm_update()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    new.updated_at = now();

    if new.active = true then
        update matching.algorithm
        set active = false
        where id != new.id;

        -- Execute refresh only if all criterias are initialized
        if (
            select count(1)
            from
            (
                select count(1)
                from matching.algorithm a
                join matching_criteriaweight mc
                    on a.level_weight_id = mc.id
                where a.active
                union
                select count(1)
                from matching.algorithm a
                join matching_criteriaweight mc
                    on a.location_weight_id = mc.id
                where a.active
                union
                select count(1)
                from matching.algorithm a
                join matching_criteriaweight mc
                    on a.sector_weight_id = mc.id
                where a.active
                union
                select count(1)
                from matching.algorithm a
                join matching_criteriaweight mc
                    on a.response_weight_id = mc.id
                where a.active) t
            where count = 0) = 0
        then
            perform matching.refresh_level_score();
            perform matching.refresh_sector_score();
            perform matching.refresh_location_score();
            perform matching.refresh_response_score();
            perform matching.refresh_total_score();
        end if;
    end if;

    return new;
end;
$$;
create trigger algorithm_update
    after update
    on matching.algorithm
    for each row
execute procedure matching.algorithm_update();

-- Update active algorithm
update matching.algorithm
set active = true
where prefix = 'penalisation';
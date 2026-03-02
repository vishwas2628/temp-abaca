create schema if not exists matching;

-- matching_supporter on insert or update

create or replace function matching_supporter_materialized_insert_update()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    if (tg_op = 'UPDATE') then
        -- Affects level update
        if old.level_weight_id != new.level_weight_id
            or old.investing_level_range != new.investing_level_range then
            perform matching.refresh_level_score(_refresh_all := false, _supporter_id := new.id);
            perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.id);
        end if;

        -- Affects sectors update
        if old.sectors_weight_id != new.sectors_weight_id then
            perform matching.refresh_sector_score(_refresh_all := false, _supporter_id := new.id);
            perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.id);
        end if;

        -- Affects location update
        if old.locations_weight_id != new.locations_weight_id then
            perform matching.refresh_location_score(_refresh_all := false, _supporter_id := new.id);
            perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.id);
        end if;

        return new;
    elsif (tg_op = 'INSERT') then
        -- Affects level, sectors, location and responses update
        perform matching.refresh_level_score(_refresh_all := false, _supporter_id := new.id);
        perform matching.refresh_sector_score(_refresh_all := false, _supporter_id := new.id);
        perform matching.refresh_location_score(_refresh_all := false, _supporter_id := new.id);
        perform matching.refresh_response_score(_refresh_all := false, _supporter_id := new.id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.id);
        return new;
    end if;
end;
$$;
drop trigger if exists matching_supporter_materialized_insert_update on matching_supporter cascade;
create trigger matching_supporter_materialized_insert_update
    after update
    on matching_supporter
    for each row
execute procedure matching_supporter_materialized_insert_update();


-- matching_supporter_sectors on insert or delete

create or replace function matching_supporter_sectors_materialized_insert_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    -- Affects sectors
    if (tg_op = 'DELETE') then
        perform matching.refresh_sector_score(_refresh_all := false, _supporter_id := old.supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := old.supporter_id);
        return old;
    elsif (tg_op = 'INSERT') then
        perform matching.refresh_sector_score(_refresh_all := false, _supporter_id := new.supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.supporter_id);
        return new;
    end if;
end;
$$;
drop trigger if exists matching_supporter_sectors_materialized_insert_delete on matching_supporter_sectors cascade;
create trigger matching_supporter_sectors_materialized_insert_delete
    after insert or delete
    on matching_supporter_sectors
    for each row
execute procedure matching_supporter_sectors_materialized_insert_delete();


-- viral_company_sectors on insert or delete

create or replace function viral_company_sectors_materialized_insert_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    -- Affects sectors
    if (tg_op = 'DELETE') then
        perform matching.refresh_sector_score(_refresh_all := false, _company_id := old.company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := old.company_id);
        return old;
    elsif (tg_op = 'INSERT') then
        perform matching.refresh_sector_score(_refresh_all := false, _company_id := new.company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := new.company_id);
        return new;
    end if;
end;
$$;
drop trigger if exists viral_company_sectors_materialized_insert_delete on viral_company_sectors cascade;
create trigger viral_company_sectors_materialized_insert_delete
    after insert or delete
    on viral_company_sectors
    for each row
execute procedure viral_company_sectors_materialized_insert_delete();

-- matching_supporter_locations on insert or delete

create or replace function matching_supporter_locations_materialized_insert_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    -- Affects locations
    if (tg_op = 'DELETE') then
        perform matching.refresh_location_score(_refresh_all := false, _supporter_id := old.supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := old.supporter_id);
        return old;
    elsif (tg_op = 'INSERT') then
        perform matching.refresh_location_score(_refresh_all := false, _supporter_id := new.supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.supporter_id);
        return new;
    end if;
end;
$$;
drop trigger if exists matching_supporter_locations_materialized_insert_delete on matching_supporter_locations cascade;
create trigger matching_supporter_locations_materialized_insert_delete
    after insert or delete
    on matching_supporter_locations
    for each row
execute procedure matching_supporter_locations_materialized_insert_delete();


-- viral_company_locations on insert or delete

create or replace function viral_company_locations_materialized_insert_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    -- Affects locations
    if (tg_op = 'DELETE') then
        perform matching.refresh_location_score(_refresh_all := false, _company_id := old.company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := old.company_id);
        return old;
    elsif (tg_op = 'INSERT') then
        perform matching.refresh_location_score(_refresh_all := false, _company_id := new.company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := new.company_id);
        return new;
    end if;
end;
$$;
drop trigger if exists viral_company_locations_materialized_insert_delete on viral_company_locations cascade;
create trigger viral_company_locations_materialized_insert_delete
    after insert or delete
    on viral_company_locations
    for each row
execute procedure viral_company_locations_materialized_insert_delete();


-- matching_criteria on insert or update or delete

create or replace function matching_criteria_materialized_insert_update_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    -- Affects responses
    if (tg_op = 'DELETE') then
        perform matching.refresh_response_score(_refresh_all := false, _supporter_id := old.supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := old.supporter_id);
        return old;
    elsif (tg_op = 'UPDATE') then
        if old.criteria_weight_id != new.criteria_weight_id
            or old.desired != new.desired then
            perform matching.refresh_response_score(_refresh_all := false, _supporter_id := new.supporter_id);
            perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.supporter_id);
        end if;

        return new;
    elsif (tg_op = 'INSERT') then
        perform matching.refresh_response_score(_refresh_all := false, _supporter_id := new.supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := new.supporter_id);
        return new;
    end if;
end;
$$;
drop trigger if exists matching_criteria_materialized_insert_update_delete on matching_criteria cascade;
create trigger matching_criteria_materialized_insert_update_delete
    after insert or delete
    on matching_criteria
    for each row
execute procedure matching_criteria_materialized_insert_update_delete();


-- matching_criteria_answers on insert or delete

create or replace function matching_criteria_answers_materialized_insert_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
declare
    _criteria_supporter_id integer;
begin
    -- Affects responses
    if (tg_op = 'DELETE') then
        -- Fetch supporter for criteria
        _criteria_supporter_id :=
                (select supporter_id from matching_criteria where matching_criteria.id = old.criteria_id);
        perform matching.refresh_response_score(_refresh_all := false, _supporter_id := _criteria_supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := _criteria_supporter_id);
        return old;
    elsif (tg_op = 'INSERT') then
        -- Fetch supporter for criteria
        _criteria_supporter_id :=
                (select supporter_id from matching_criteria where matching_criteria.id = new.criteria_id);
        perform matching.refresh_response_score(_refresh_all := false, _supporter_id := _criteria_supporter_id);
        perform matching.refresh_total_score(_refresh_all := false, _supporter_id := _criteria_supporter_id);
        return new;
    end if;
end;
$$;
drop trigger if exists matching_criteria_answers_materialized_insert_delete on matching_criteria_answers cascade;
create trigger matching_criteria_answers_materialized_insert_delete
    after insert or delete
    on matching_criteria_answers
    for each row
execute procedure matching_criteria_answers_materialized_insert_delete();


-- matching_response on insert or update or delete

create or replace function matching_response_materialized_insert_update_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
declare
    _criteria_company_id integer;
begin
    -- Affects responses
    if (tg_op = 'DELETE') then
        -- Fetch company with user profile
        _criteria_company_id :=
                (select company_id from viral_userprofile where viral_userprofile.id = old.user_profile_id);
        perform matching.refresh_response_score(_refresh_all := false, _company_id := _criteria_company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := _criteria_company_id);
        return old;
    elsif (tg_op = 'UPDATE') then
        if old.value != new.value then
            -- Fetch company with user profile
            _criteria_company_id :=
                    (select company_id from viral_userprofile where viral_userprofile.id = new.user_profile_id);
            perform matching.refresh_response_score(_refresh_all := false, _company_id := _criteria_company_id);
            perform matching.refresh_total_score(_refresh_all := false, _company_id := _criteria_company_id);
        end if;

        return new;
    elsif (tg_op = 'INSERT') then
        -- Fetch company with user profile
        _criteria_company_id :=
                (select company_id from viral_userprofile where viral_userprofile.id = new.user_profile_id);
        perform matching.refresh_response_score(_refresh_all := false, _company_id := _criteria_company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := _criteria_company_id);
        return new;
    end if;
end;
$$;
drop trigger if exists matching_response_materialized_insert_update_delete on matching_response cascade;
create trigger matching_response_materialized_insert_update_delete
    after insert or delete
    on matching_response
    for each row
execute procedure matching_response_materialized_insert_update_delete();


-- matching_response_answers on insert or delete

create or replace function matching_response_answers_materialized_insert_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
declare
    _criteria_company_id integer;
begin
    -- Affects responses
    if (tg_op = 'DELETE') then
        -- Fetch company with user profile
        _criteria_company_id := (
            select company_id
            from viral_userprofile
                     join matching_response on viral_userprofile.id = matching_response.user_profile_id
            where matching_response.id = old.response_id);
        perform matching.refresh_response_score(_refresh_all := false, _company_id := _criteria_company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := _criteria_company_id);
        return old;
    elsif (tg_op = 'INSERT') then
        -- Fetch company with user profile
        _criteria_company_id := (
            select company_id
            from viral_userprofile
                     join matching_response on viral_userprofile.id = matching_response.user_profile_id
            where matching_response.id = new.response_id);
        perform matching.refresh_response_score(_refresh_all := false, _company_id := _criteria_company_id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := _criteria_company_id);
        return new;
    end if;
end;
$$;
drop trigger if exists matching_response_answers_materialized_insert_delete on matching_response_answers cascade;
create trigger matching_response_answers_materialized_insert_delete
    after insert or delete
    on matching_response_answers
    for each row
execute procedure matching_response_answers_materialized_insert_delete();


-- grid_assessment on insert

create or replace function grid_assessment_materialized_insert()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    -- Affects levels
    perform matching.refresh_level_score(_refresh_all := false, _company_id := new.evaluated);
    perform matching.refresh_total_score(_refresh_all := false, _company_id := new.evaluated);
    return new;
end;
$$;
drop trigger if exists grid_assessment_materialized_insert on grid_assessment cascade;
create trigger grid_assessment_materialized_insert
    after insert
    on grid_assessment
    for each row
execute procedure grid_assessment_materialized_insert();


-- viral_company on insert or delete

create or replace function viral_company_materialized_insert_delete()
    returns trigger
    security definer
    language plpgsql
as
$$
begin
    -- Impacts levels, locations, sectors and responses scores
    if (tg_op = 'DELETE') then
        perform matching.refresh_level_score(_refresh_all := false, _company_id := old.id);
        perform matching.refresh_location_score(_refresh_all := false, _company_id := old.id);
        perform matching.refresh_sector_score(_refresh_all := false, _company_id := old.id);
        perform matching.refresh_response_score(_refresh_all := false, _company_id := old.id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := old.id);
        return old;
    elsif (tg_op = 'INSERT') then
        perform matching.refresh_level_score(_refresh_all := false, _company_id := new.id);
        perform matching.refresh_location_score(_refresh_all := false, _company_id := new.id);
        perform matching.refresh_sector_score(_refresh_all := false, _company_id := new.id);
        perform matching.refresh_response_score(_refresh_all := false, _company_id := new.id);
        perform matching.refresh_total_score(_refresh_all := false, _company_id := new.id);
        return new;
    end if;
end;
$$;
drop trigger if exists viral_company_materialized_insert_delete on viral_company cascade;
create trigger viral_company_materialized_insert_delete
    after insert or delete
    on viral_company
    for each row
execute procedure viral_company_materialized_insert_delete();
create schema if not exists matching;

-- Create algorithm table

drop table if exists matching.algorithm cascade;
create table matching.algorithm
(
    id                 serial primary key,
    name               varchar,
    active             bool,
    prefix             varchar not null,
    level_weight_id    integer                     default 4,
    location_weight_id integer                     default 5,
    sector_weight_id   integer                     default 5,
    response_weight_id integer                     default 1,
    created_at         timestamp without time zone default now(),
    updated_at         timestamp without time zone default now()
);


-- Trigger for algorithm on update

drop function if exists matching.algorithm_update();
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
    end if;

    return new;
end;
$$;
drop trigger if exists algorithm_update on matching.algorithm cascade;
create trigger algorithm_update
    before update
    on matching.algorithm
    for each row
execute procedure matching.algorithm_update();


-- Insert algorithms - initial, exclusion and penalisation

insert into matching.algorithm(name, prefix, active)
values ('initial@1.0.0', 'initial', false),
       ('exclusion@1.0.0', 'exclusion', true),
       ('penalisation@1.0.0', 'penalisation', false);


-- Common entrepreneur supporter view

drop view if exists matching.entrepreneur_supporter_view;
create or replace view matching.entrepreneur_supporter_view as
(
select distinct vc.id                    as company_id,
                ms.id                    as supporter_id,
                ms.investing_level_range as supporter_level_range,
                ms.sectors_weight_id     as sector_weight_id,
                cw.value                 as sector_score,
                ms.level_weight_id       as level_weight_id,
                cw1.value                as level_score,
                ms.locations_weight_id   as location_weight_id,
                cw2.value                as location_score
from (select id
      from viral_company
      where type = 0) vc, -- Grab only entrepreneurs
     matching_supporter ms
         left outer join matching_criteriaweight cw
                         on cw.id = ms.sectors_weight_id
         left outer join matching_criteriaweight cw1
                         on cw1.id = ms.level_weight_id
         left outer join matching_criteriaweight cw2
                         on cw2.id = ms.locations_weight_id
    );

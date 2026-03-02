-- Track ongoing matching calculations
drop table if exists matching.ongoing_calculations cascade;
create table matching.ongoing_calculations
(
    id           SERIAL,
    company_id   integer NULL,
    supporter_id integer NULL,
    created_at   timestamp without time zone default now(),
    primary key (id)
);

-- Create function to signal the start of a calculation
drop function if exists matching.signal_calculation_start(_company_id integer, _supporter_id integer);
create or replace function matching.signal_calculation_start(_company_id integer default null,
                                                        _supporter_id integer default null)
    returns void
as
$$
begin
    -- Add new calculation
    insert into matching.ongoing_calculations (company_id, supporter_id)
    values (_company_id, _supporter_id);
end;
$$
    language plpgsql;

-- Create function to signal the end of a calculation
drop function if exists matching.signal_calculation_end(_company_id integer, _supporter_id integer);
create or replace function matching.signal_calculation_end(_company_id integer default null,
                                                        _supporter_id integer default null)
    returns void
as
$$
begin
    -- Remove ongoing calculation
    delete from matching.ongoing_calculations
    where id in (select id from matching.ongoing_calculations 
      where company_id = _company_id or supporter_id = _supporter_id 
      order by created_at asc limit 1);
end;
$$
    language plpgsql;
-- Update function to signal the end of a calculation by also removing old stale calculations 
drop function if exists matching.signal_calculation_end(_company_id integer, _supporter_id integer);
create or replace function matching.signal_calculation_end(_company_id integer default null,
                                                        _supporter_id integer default null)
    returns void
as
$$
begin
    -- Remove ongoing calculation & stale ones
    delete from matching.ongoing_calculations
    where id in (select distinct on (created_at::date) id from matching.ongoing_calculations 
      where company_id = _company_id or supporter_id = _supporter_id 
      and created_at < now()
      order by created_at::date asc);
end;
$$
    language plpgsql;
function p = ka_case(p, pcase, window)
%KA_CASE  Same flow tables, another pressure case and / or window (no new tables).
%   p = ka_case(p, pcase, window)   pcase 1 = 20 kPa, 2 = 27 kPa; window 1 or 2
%   The fill timing (p.fill_floor, p.t_fill_demand) is reset: call
%   ka_fill_timing again before demand-pulse runs.
p = ka_set_option(p, pcase);
p = ka_set_window(p, window);
p = ka_derived(p);
p.fill_floor = NaN;  p.t_fill_demand = NaN;
p.hw_status = sprintf('PROPOSED, NOT APPROVED - Rev 27, %s, %s, %d MHJ10', p.opt_name, p.win_name, p.n_in);
end

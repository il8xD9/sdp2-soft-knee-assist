function m = ka_metrics_pulse(p, res)
%KA_METRICS_PULSE  Cap keeping, exposure and venting of one controlled pulse (N2, N3).
L = res.log;  t = L.t;  pg = L.p;  dtl = p.dt * res.cfg.log_every;
cap = p.cap_kPa;
tf = res.ev.fill(1);
if isempty(res.ev.offset), toff = NaN; else, toff = res.ev.offset(1); end
i2 = find(pg >= 0.98 * cap, 1, 'first');
if isempty(i2)
    m.fill2_ms = NaN;  m.mean_err_kPa = NaN;
else
    m.fill2_ms = (t(i2) - tf) * 1e3;                      % fill command -> within 2 % of the cap
    hold = t >= t(i2) & t < toff;
    m.mean_err_kPa = mean(abs(cap - pg(hold)));
end
m.peak_kPa = max(pg);
m.over_kPa = max(pg) - cap;
a = find(pg > p.rest_kPa);
m.above_ms = numel(a) * dtl * 1e3;                        % time above 2.4 kPa(g)
if isempty(a)
    m.deflated_ms = NaN;  m.back_rest_ms = NaN;
else
    m.deflated_ms  = (t(a(end)) + dtl - toff) * 1e3;      % after the window offset
    m.back_rest_ms = (t(a(end)) + dtl) * 1e3;
end
io = L.inopen > 0.5;
m.inlet_pulses = sum(io(2:end) & ~io(1:end-1));           % real inlet openings
m.exh_corr = res.n_ex_edges;                              % exhaust correction pulses
m.p_onset_kPa = interp1(t, pg, p.t_on);
end

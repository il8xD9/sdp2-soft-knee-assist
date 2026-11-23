function m = ka_metrics_fault(p, res)
%KA_METRICS_FAULT  N5 measures of a fault run.
%   vented_ms  time from the fault until the bladder is at or below 2.4 kPa(g) for good
%   peak_kPa   highest bladder pressure
L = res.log;  dtl = p.dt * res.cfg.log_every;
a = find(L.p > p.rest_kPa, 1, 'last');
if isempty(a)
    m.vented_ms = 0;
else
    m.vented_ms = (L.t(a) + dtl - res.cfg.t_fault) * 1e3;
end
m.peak_kPa = max(L.p);
end

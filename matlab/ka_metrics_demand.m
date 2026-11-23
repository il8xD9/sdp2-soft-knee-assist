function m = ka_metrics_demand(p, res, T_stance)
%KA_METRICS_DEMAND  N1, N4 and N6 measures against the TRUE window (contact at t = 0).
%   onset_pct    bladder pressure at the true onset / onset demand (N1-1)
%   before_pct   torque x time before the true onset / torque x time asked (N1-2)
%   missing_pct  torque x time missing in the window / asked (N1-3)
%   over_pct     torque x time above the asked curve in the window / asked (information)
%   peak_pct     peak device torque / peak target torque
%   impulse_Nms  device torque x time inside the window (N m s)
%   first_above_ms, back_rest_ms   first above 2.4 kPa(g), back at 2.4 kPa(g)
%   p_straight_kPa  highest pressure while the knee is at or past straight (N4-4)
%   p_deadline_kPa  pressure at the push-off deadline (N4-1); margin_ms to it
%   Rev 27: the target is tau_req (ka_torque_req: window 2 capped at the patient's
%   moment) limited to k x set point; torque = k3D x pressure.
if nargin < 3, T_stance = p.T_stance; end
L = res.log;  t = L.t;  dtl = t(min(2, numel(t))) - t(1);
if dtl <= 0, dtl = p.dt * res.cfg.log_every; end
pg = max(L.p, 0);
k = p.k_Nm_per_kPa;  cap = p.cap_kPa;
t_on  = p.win_on_pct  / 100 * T_stance;
t_off = p.win_off_pct / 100 * T_stance;
inw = t >= t_on & t <= t_off;
tgt = zeros(size(t));
tgt(inw) = min(ka_torque_req(p, t(inw), T_stance), k * cap);
dev = k * pg;
asked = sum(tgt(inw)) * dtl;
m.before_pct  = sum(dev(t < t_on)) * dtl / asked * 100;
m.missing_pct = sum(max(tgt(inw) - dev(inw), 0)) * dtl / asked * 100;
m.over_pct    = sum(max(dev(inw) - tgt(inw), 0)) * dtl / asked * 100;
m.after_pct   = sum(dev(t > t_off)) * dtl / asked * 100;
m.peak_pct    = max(dev) / max(tgt) * 100;
m.impulse_Nms = sum(dev(inw)) * dtl;
m.asked_Nms   = asked;
m.onset_pct   = interp1(t, L.p, t_on) / p.p_on_kPa * 100;
a = find(L.p > p.rest_kPa);
if isempty(a)
    m.first_above_ms = NaN;  m.back_rest_ms = NaN;
else
    m.first_above_ms = t(a(1)) * 1e3;
    m.back_rest_ms   = (t(a(end)) + dtl) * 1e3;
end
knee = interp1(p.b4_t, p.b4_deg, t, 'linear', 'extrap');
i0 = find(knee > 0, 1, 'first');
m.t_knee0_ms = t(i0) * 1e3;
m.p_straight_kPa = max(L.p(t <= t(i0)));
t_dl = p.deadline_pct / 100 * T_stance;
m.p_deadline_kPa = interp1(t, L.p, t_dl);
m.margin_ms = (t_dl - m.back_rest_ms / 1e3) * 1e3;
m.peak_kPa = max(L.p);
% fastest rise and fall the demand asks for
tg = (t_on : 1e-4 : t_off);
dem = min(ka_torque_req(p, tg, T_stance) / k, cap);
[m.max_demand_rate, im] = max(diff(dem) / 1e-4);
m.t_max_demand_rate_ms = tg(im) * 1e3;
m.max_demand_fall = -min(diff(dem) / 1e-4);
end

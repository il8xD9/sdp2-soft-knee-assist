function [floor_w, fill_w, scan] = ka_fill_timing(p)
%KA_FILL_TIMING  G-5 floor and demand-pulse fill command (Rev 23 rules, Rev 27 search).
%   [floor_w, fill_w] = ka_fill_timing(p)      times on the window clock (s)
%   [~, ~, scan] = ...                         scan = [fill command (s), onset % slowest case]
%
%   G-5 floor (D-B4-4): the earliest fill command for which the fastest case
%   (no heat exchange, receiver 70 kPa(g)) stays at or below 2.4 kPa(g) until
%   43 ms (1 ms past the 42 ms at which the knee passes 0 deg) with the window
%   clock 4 ms early (Rev 23 footswitches, +-4 ms). Bisection.
%
%   Fill command: the latest command, on a 0.5 ms grid from the floor to the
%   onset - 2.5 ms, at which the slowest case (room temperature, receiver
%   53 kPa(g)) still holds at least MIN(91 %, best - 1 point) of the onset
%   demand at the window onset. Rev 27: the onset is 59.4 ms (window 1) or
%   91.65 ms (window 2). Rev 25 kept the best onset within 1 point; in window 2
%   that put the fill 50 ms before the onset and pushed 11 % of the torque x time
%   early (N1-2), so Rev 27 waits as long as N1-1 (90 %, +1 point margin)
%   allows. The search scans every 2 ms and then the 0.5 ms points of the last
%   passing step. Complete system: p.n_exh_sys MHE3 at the port.
f = @(fw) 2.4 - max_until(p, fw);
floor_w = bisect(f, 0.020, 0.059);
g0 = ceil(floor_w * 2000) / 2000;
g1 = p.t_on - 0.0025;
coarse = g0 : 0.002 : g1;
pc = arrayfun(@(fw) onset_pct(p, fw), coarse);
best = max(pc);
thr = min(91, best - 1);          % Rev 27: N1-1 level 90 % + 1 point, or best - 1 if that is lower
ok = find(pc >= thr, 1, 'last');
fine = coarse(ok) + (0.0005 : 0.0005 : 0.0015);
fine = fine(fine <= g1);
pf = arrayfun(@(fw) onset_pct(p, fw), fine);
grid_w = [coarse, fine];  pct = [pc, pf];
okf = find(pf >= thr, 1, 'last');
if isempty(okf)
    fill_w = coarse(ok);
else
    fill_w = fine(okf);
end
[grid_w, is] = sort(grid_w);  pct = pct(is);
scan = [grid_w(:), pct(:)];
end

function v = onset_pct(p, fw)
c = ka_default_cfg('pulse','demand','adiabatic',false,'pr_kPa',53,'n_exh',p.n_exh_sys, ...
                   'exh_at_port',true,'fill_at',fw,'t_end',p.t_on + 0.004);
r = ka_simulate(p, c);
v = interp1(r.log.t, r.log.p, p.t_on) / p.p_on_kPa * 100;
end

function mx = max_until(p, fw)
c = ka_default_cfg('pulse','demand','adiabatic',true,'pr_kPa',70,'n_exh',p.n_exh_sys,'exh_at_port',true, ...
                   'clock_err',-0.004,'fill_at',fw,'t_end',0.08);
r = ka_simulate(p, c);
mx = max([0; r.log.p(r.log.t <= p.knee0_t + 1e-3)]);
end

function x = bisect(f, a, b)
% root of an increasing function on [a, b]
fa = f(a);  fb = f(b);
if fa >= 0, x = a; return, end
if fb <= 0, x = b; return, end
for it = 1:30
    x = 0.5 * (a + b);
    if f(x) > 0, b = x; else, a = x; end
    if b - a < 1e-5 * max(1, abs(b)), break, end
end
x = 0.5 * (a + b);
end

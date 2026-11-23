function res = ka_simulate(p, cfg)
%KA_SIMULATE  One run of the pneumatic system (explicit Euler, p.dt).
%   res = ka_simulate(p, cfg)   p from ka_setup (or ka_params + ka_prepare),
%                               cfg from ka_default_cfg
%
%   Each step:  sensor (1.0 ms delay) -> ka_logic_step (controller board)
%               -> valve delays (inlet opens 1.0 / closes 0.5 ms; exhaust
%               shuts 2.53 / opens 3.08 ms) -> relief valve (if fitted)
%               -> ka_plant_deriv -> Euler update.
%   The Simulink model (build_ka_simulink.m) has the same blocks in the same order.
%
%   res.log : t, p (kPa(g)), pm, r, u, uff, pr, T, inopen, exopen, incmd, w, stage, pump, relief
%   res     : air_mL (ANR) drawn from the receiver, pump_time, pump_starts,
%             pr_min/max, t_fill_w, ev (event times), counters

dt = p.dt;  patm = p.p_atm;
if isnan(cfg.t_end), t_end = cfg.n_strides * p.T_stride; else, t_end = cfg.t_end; end
n = round(t_end / dt);
d_in_on  = round(p.in_t_open / dt);   d_in_off = round(p.in_t_close / dt);
d_ex_on  = round(p.exh_t_close / dt); d_ex_off = round(p.exh_t_open / dt);
d_sen    = round(p.sens_delay / dt);
NB = max(1024, 2^ceil(log2(max([d_in_on d_in_off d_ex_on d_ex_off d_sen]) + 2)));   % history length
if cfg.n_exh < 1 || cfg.n_exh > p.ex_nmax
    error('ka_simulate: n_exh must be 1..%d', p.ex_nmax);
end

[~, ~, ~, ~, ~, S] = ka_logic_step('init', p, cfg);
in0 = S.in0;  ex0 = S.ex0;
S = []; %#ok<NASGU>  % drop the reference so the persistent memory is updated in place
P  = cfg.p0_kPa * 1e3 + patm;
m  = P * p.V / (p.R * p.T0);
pr = cfg.pr_kPa;
hp = repmat(cfg.p0_kPa, 1, NB);                  % pressure history (sensor delay)
if in0
    % filling before the fault: the readings of the last ms were lower (the sensor lags the rise)
    dP0 = ka_plant_deriv(P, m, pr, true, 0, false, p, false, false, cfg.exh_at_port) / 1e3;
    for j = 1:NB-1
        hp(mod(-j, NB) + 1) = max(cfg.p0_kPa - dP0 * j * dt, 0);
    end
end
hi = repmat(in0, 1, NB);                         % inlet command history
h1 = repmat(ex0, 1, NB);  h2 = h1;               % exhaust command histories (1 = powered)
n_rest = cfg.n_exh - 1;                          % exhausts in group 2
adi = cfg.adiabatic;  rdyn = cfg.receiver_dynamic;  port = cfg.exh_at_port;
rel_on = p.relief_on;  rel_open = false;
air = 0;  pr_min = pr;  pr_max = pr;
stop_v = isfield(cfg, 'stop_vented') && cfg.stop_vented;

le = cfg.log_every;  nl = floor((n - 1) / le) + 1;
L.t = zeros(nl,1); L.p = L.t; L.pm = L.t; L.r = nan(nl,1); L.u = L.r; L.uff = L.r; L.pr = L.t; L.T = L.t;
L.inopen = L.t; L.exopen = L.t; L.incmd = L.t; L.w = L.t; L.stage = L.t; L.pump = L.t; L.relief = L.t;
li = 0;

for k = 0:n-1
    pg = (P - patm) / 1e3;
    ib = mod(k, NB) + 1;
    hp(ib) = pg;
    pm = hp(mod(k - d_sen, NB) + 1);                                   % sensor 1.0 ms
    [in_cmd, e1_pow, e2_pow, pump, w, dg] = ka_logic_step('step', k, pm, pr);
    hi(ib) = in_cmd;  h1(ib) = e1_pow;  h2(ib) = e2_pow;
    in_open = hi(mod(k - d_in_on, NB) + 1) && hi(mod(k - d_in_off, NB) + 1);       % min of delays
    e1_open = ~(h1(mod(k - d_ex_on, NB) + 1) || h1(mod(k - d_ex_off, NB) + 1));     % max of delays
    e2_open = n_rest > 0 && ~(h2(mod(k - d_ex_on, NB) + 1) || h2(mod(k - d_ex_off, NB) + 1));
    n_open = double(e1_open) + double(e2_open) * n_rest;
    if rel_on                                                          % L500 with hysteresis
        if ~rel_open && pg >= p.rel_crack_kPa
            rel_open = true;
        elseif rel_open && pg <= p.rel_reseat_kPa
            rel_open = false;
        end
    end
    [dP, dm, dpr, md_in, ~, T] = ka_plant_deriv(P, m, pr, in_open, n_open, pump, p, adi, rdyn, port, rel_open);
    if mod(k, le) == 0
        li = li + 1;
        L.t(li) = k*dt;  L.p(li) = pg;  L.pm(li) = pm;
        if dg(3) == 2, L.r(li) = dg(1); L.u(li) = dg(2); L.uff(li) = dg(4); end
        L.pr(li) = pr;  L.T(li) = T;  L.inopen(li) = in_open;  L.exopen(li) = n_open;
        L.incmd(li) = in_cmd;  L.w(li) = w;  L.stage(li) = dg(3);  L.pump(li) = pump;  L.relief(li) = rel_open;
    end
    % early end of fault runs (cfg.stop_vented): safe state reached and the bladder at rest.
    % With the supply off it never comes back, the inlet stays shut and all exhausts stay
    % open, so the pressure can only fall from here.
    if stop_v && mod(k, 100) == 0 && pg <= p.rest_kPa && ~in_open && n_open == cfg.n_exh
        [~, ~, ~, ~, ~, Sg] = ka_logic_step('get');
        off = ~Sg.supply;  Sg = []; %#ok<NASGU>
        if off, break, end
    end
    P  = P  + dP * dt;
    m  = m  + dm * dt;
    pr = pr + dpr * dt;
    air = air + md_in * dt;
    if pr < pr_min, pr_min = pr; end
    if pr > pr_max, pr_max = pr; end
end
fn = fieldnames(L);
for i = 1:numel(fn), L.(fn{i}) = L.(fn{i})(1:li); end

[~, ~, ~, ~, ~, S] = ka_logic_step('get');
res.log = L;
res.air_mL = air / p.rho_anr * 1e6;
res.pump_time = S.pump_time;  res.pump_hi = S.pump_hi;  res.pump_starts = S.pump_starts;
res.n_ex_edges = S.n_ex_edges;  res.in_on_t = S.in_on_t;  res.ex_pow_t = S.ex_pow_t;
res.pr_min = pr_min;  res.pr_max = pr_max;  res.t_fill_w = S.t_fill_w;
res.ev = S.ev;  res.cfg = cfg;  res.t_supply_off = S.t_off_supply;  res.t_end = t_end;
end

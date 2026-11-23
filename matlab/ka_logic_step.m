function [in_cmd, e1_pow, e2_pow, pump, w, S] = ka_logic_step(cmd, a1, a2, a3)
%KA_LOGIC_STEP  The controller board, one time step: contact rules G-1..G-5,
%   window clock, PI + feedforward + anti-windup (Rev 22), 200 Hz PWM (one
%   pulse per period), faults, hardware trip, watchdog, 24 V supply switch and
%   the receiver pump switch.
%
%   ka_logic_step('init', p, cfg)     reset all memory for a new run
%   [in_cmd, e1_pow, e2_pow, pump, w] = ka_logic_step('step', k, pm, pr)
%        k   step index (t = k*dt, k = 0, 1, 2, ...)
%        pm  controller sensor reading, kPa(g) (already 1.0 ms old)
%        pr  receiver pressure, kPa(g)
%        in_cmd  inlet MHJ10 command, all p.n_in valves (1 = energised = open)
%        e1_pow  exhaust 1 command (1 = energised = SHUT); exhaust 1 makes the corrections
%        e2_pow  command of the other cfg.n_exh - 1 exhausts (one group)
%        pump    pump running (switch on and supply on)
%        w       window clock (s), -1 before the first contact
%   [..., dg] = ka_logic_step('step', ...) also returns dg = [r u stage uff]
%   [~,~,~,~,~,S] = ka_logic_step('get')   memory, counters and events
%
%   The same function runs inside ka_simulate.m and inside the Simulink
%   model (sl_ka_logic.m), so both use identical control code.
%
%   Rev 27: the reference is tau_req / k from ka_torque_req (window option 2:
%   MIN(alpha x deficit, patient moment); window option 1: alpha x deficit),
%   with the 3D torque constant k3D.
%   Rev 25 against Rev 21: no D term and no cap guard (Rev 22); feedforward on
%   the release through one exhaust; set point = B7 limit; two footswitches read
%   at 1 kHz with the window clock at detection - 5.6 ms (Rev 23); fill command
%   from ka_fill_timing (p.t_fill_demand), never before the G-5 floor;
%   forced abort cfg.abort_w and the 'stuck_all' fault (relief-valve runs).

persistent S0
switch cmd
    case 'init'
        S0 = init_state(a1, a2);
        in_cmd = S0.in0; e1_pow = S0.ex0; e2_pow = S0.ex0; pump = false; w = -1; S = S0;
        return
    case 'get'
        in_cmd = false; e1_pow = false; e2_pow = false; pump = false; w = -1; S = S0;
        return
    case 'step'
        % continue below
    otherwise
        error('ka_logic_step: unknown command %s', cmd);
end

k = a1;  pm = a2;  pr = a3;
p = S0.p;  cfg = S0.cfg;  dt = p.dt;
t = k * dt;

%% ================= contact rules and window clock =================
if S0.pulse_code > 0
    if S0.contact_ideal
        % window clock placed directly at each stride start + clock error
        s_idx = floor((t - cfg.clock_err) / p.T_stride + 1e-9);
        if s_idx > S0.last_stride
            S0.last_stride = s_idx;
            S0.w0 = s_idx * p.T_stride + cfg.clock_err;
            S0.active = true;  S0.stage = 0;
            S0.ev.detect(end+1) = t;  S0.ev.stride_pr(end+1) = pr;
        end
    elseif k == S0.k_next_foot
        % footswitch sample at 1 kHz; the signal lags the true contact by the
        % insole delay and the 100 Hz filter (Rev 23, Section 3.3)
        S0.k_next_foot = S0.k_next_foot + S0.n_foot;
        c = contact_true(cfg, p, t - S0.sense_lag, S0.stance);
        if ~S0.active
            if c && S0.armed                                   % G-3 re-armed, G-4 new contact
                S0.w0 = t - p.clock_offset + cfg.clock_err;    % G-1 clock at detection - 5.6 ms
                S0.active = true;  S0.armed = false;  S0.stage = 0;
                S0.ev.detect(end+1) = t;  S0.ev.stride_pr(end+1) = pr;
            elseif ~c
                S0.armed = true;
            end
        elseif ~c && cfg.abort_rule && (t - S0.w0) < p.t_off
            S0.active = false;  S0.stage = 3;                  % G-2 abort and vent at once
            S0.armed = true;                                   % ... and re-arm
            S0.ev.abort(end+1) = t;
        end
    end
end
if isnan(S0.w0), w = -1; else, w = t - S0.w0; end
if S0.active
    if S0.stage == 0 && w >= S0.t_fill_w                       % exhausts powered shut first
        S0.stage = 1;  S0.ev.fill(end+1) = t;
    end
    if S0.stage == 1 && w >= S0.t_fill_w + S0.stagger          % inlet 1.53 ms later
        S0.stage = 2;  S0.k_en = k;  S0.I = 0;
        S0.per_start_k = k;  S0.ended = false;  S0.chan = 0;
        S0.ev.enable(end+1) = t;
    end
    if S0.stage == 2 && w >= p.t_off                           % window offset: vent
        S0.stage = 3;  S0.active = false;  S0.ev.offset(end+1) = t;
    end
    if S0.active && ~isnan(cfg.abort_w) && w >= cfg.abort_w    % forced G-2 abort (false contact)
        S0.stage = 3;  S0.active = false;  S0.ev.offset(end+1) = t;  S0.ev.abort(end+1) = t;
    end
end

%% ================= controller 1 kHz and PWM 200 Hz =================
if S0.stage == 2
    kr = k - S0.k_en;
    if mod(kr, S0.n_ctrl) == 0
        S0 = controller(S0, kr, w, pm, pr);
    end
    if mod(kr, S0.n_pwm) == 0                                  % new PWM period
        S0.per_start_k = k;  S0.ended = false;
        S0.chan = sign(S0.u);
    end
    u = S0.u;
    same = (u > 0 && S0.chan == 1) || (u < 0 && S0.chan == -1);
    if same, ton = abs(u) * p.Tpwm; else, ton = 0; end
    if ~S0.ended && (k - S0.per_start_k) * dt >= ton - 1e-12   % shortened, never restarted
        S0.ended = true;
    end
    on = ~S0.ended && S0.chan ~= 0;
    in_cmd = on && S0.chan == 1;
    e1_pow = ~(on && S0.chan == -1);                           % one exhaust makes the corrections
    e2_pow = true;
elseif S0.stage == 1
    in_cmd = false;  e1_pow = true;  e2_pow = true;
elseif S0.pulse_code > 0
    in_cmd = false;  e1_pow = false;  e2_pow = false;          % rest / vent: all exhausts open
else
    in_cmd = S0.in0;  e1_pow = S0.ex0;  e2_pow = S0.ex0;
end

%% ================= faults =================
if S0.fault_code > 0 && t >= cfg.t_fault
    switch S0.fault_code
        case 1      % power loss
            if S0.supply
                S0.supply = false;  S0.t_off_supply = t;
            end
        case 2      % program frozen in the hold state
            in_cmd = false;  e1_pow = true;  e2_pow = true;
            if cfg.watchdog && S0.supply && t >= cfg.t_fault + p.t_wd
                S0.supply = false;  S0.t_off_supply = t;
            end
        case 3      % inlet held open (frozen while filling or shorted driver)
            in_cmd = true;  e1_pow = true;  e2_pow = true;
            if cfg.watchdog && S0.supply && t >= cfg.t_fault + p.t_wd
                S0.supply = false;  S0.t_off_supply = t;
            end
        case 4      % controller, trip and watchdog all failed, power on (relief-valve check)
            in_cmd = true;  e1_pow = true;  e2_pow = true;
    end
end

%% ================= over-pressure trip (own sensor, no software) =================
if ~isnan(cfg.trip_kPa) && S0.supply
    if ~S0.tripped && pm - cfg.trip_err_kPa >= cfg.trip_kPa
        S0.tripped = true;  S0.t_trip = t + p.trip_extra;
    end
    if S0.tripped && t >= S0.t_trip - 1e-12
        S0.supply = false;  S0.t_off_supply = t;
    end
end

%% ================= 24 V supply switches open = safe state =================
if ~S0.supply
    in_cmd = false;
    if t >= S0.t_off_supply + p.supply_holdup - 1e-12
        e1_pow = false;  e2_pow = false;
    end
end

%% ================= pump switch, receiver 55 / 70 kPa(g) =================
if cfg.receiver_dynamic
    if pr <= p.pump_on_kPa && ~S0.pump_on
        S0.pump_on = true;  S0.pump_starts = S0.pump_starts + 1;
    elseif pr >= p.pump_off_kPa
        S0.pump_on = false;
    end
    if S0.pump_on && S0.supply
        S0.pump_time = S0.pump_time + dt;
        if pr > 70, S0.pump_hi = S0.pump_hi + dt; end
    end
end
pump = S0.pump_on && S0.supply;

%% ================= bookkeeping =================
e1o = ~e1_pow;
if S0.stage == 2 && e1o && ~S0.last_e1o
    S0.n_ex_edges = S0.n_ex_edges + 1;
end
S0.last_e1o = e1o;
if in_cmd, S0.in_on_t = S0.in_on_t + dt; end
S0.ex_pow_t = S0.ex_pow_t + dt * (double(e1_pow) + double(e2_pow) * (cfg.n_exh - 1));
if nargout > 5
    S = [S0.r, S0.u, S0.stage, S0.uff];      % diagnostics for the log
else
    S = [];
end
end

%% =====================================================================
function S = controller(S, kr, w, pm, pr)
% PI + feedforward + anti-windup (Xavier 2022 Sec. 4.4 Eq. 36). Runs every 1 ms.
p = S.p;  dt = p.dt;  cap = S.cap;
tau  = kr * dt;                          % time since the inlet command was enabled
taur = tau - p.sens_delay;  wr = w - p.sens_delay;
% ---- reference, compared with the reading 1.0 ms later ----
if S.pulse_code == 1
    r = min(ka_ff(p, 'value', taur), cap);                       % bounding pulse
elseif wr < p.t_on
    r = min(ka_ff(p, 'value', taur), p.p_on_kPa);                % rise to the onset demand
else
    r = min(ka_torque_req(p, wr) / S.kt, cap);                   % tau_req / k (Rev 27: window 2 cap)
end
S.r = r;
e = r - pm;
% ---- feedforward (Xavier 2022 Eq. 14) ----
if mod(kr, S.n_pwm) == 0
    tau_ps = tau;
else
    tau_ps = (S.per_start_k - S.k_en) * dt;
end
uff = 0;
if p.use_ff
    if tau < S.tau_stop
        % 1 along the fastest fill, ending 0.5 ms (inlet closing time) before it stops
        uff = min(max((S.tau_stop - p.in_t_close - tau_ps) / p.Tpwm, 0), 1);
    elseif S.pulse_code == 2 && wr >= p.t_on
        r2 = min(ka_torque_req(p, wr + p.Ts) / S.kt, cap);
        rate = (r2 - r) / p.Ts;
        if rate > 0
            full = p.R * p.T0 / p.V * ka_lookup_in(p, pr, max(pm, 0)) / 1e3;
            if full > 0, uff = min(rate / full, 1); end
        elseif rate < 0 && p.use_ff_release && (~p.ff_release_gate || pm >= r - p.ff_gate_kPa)
            % Rev 27: the release feedforward acts only once the bladder has caught up with the
            % reference (within p.ff_gate_kPa); while it still lags below, no negative feedforward
            fe = p.R * p.T0 / p.V * ka_lookup_ex(p, S.excol1, max(pm, 0)) / 1e3;
            if fe > 0, uff = max(rate / fe, -1); end
        end
    end
end
% ---- PI ----
v  = uff + p.kp * e + S.I;
us = min(max(v, -1), 1);
% ---- anti-windup: conditional integration ----
integ = true;
if p.use_aw && ((v > 1 && e > 0) || (v < -1 && e < 0))
    integ = false;
end
if integ, S.I = S.I + p.ki * e * p.Ts; end
S.u = us;  S.uff = uff;
end

function c = contact_true(cfg, p, t, stance)
if ~isempty(cfg.contacts)
    c = any(t >= cfg.contacts(:,1) & t < cfg.contacts(:,2));
else
    c = t >= 0 && mod(t, p.T_stride) < stance;
end
end

%% =====================================================================
function S = init_state(p, cfg)
S.p = p;  S.cfg = cfg;
dt = p.dt;
S.n_ctrl   = round(p.Ts / dt);          S.n_pwm    = round(p.Tpwm / dt);
S.in0 = strcmp(cfg.init, 'filling');
S.ex0 = any(strcmp(cfg.init, {'filling', 'holding'}));
S.cap = p.cap_kPa;  S.kt = p.k_Nm_per_kPa;  S.alpha = p.alpha;
S.excol1 = 1 + p.ex_nmax * double(logical(cfg.exh_at_port));   % one exhaust (release feedforward)
switch cfg.pulse
    case 'bounding', S.pulse_code = 1;
    case 'demand',   S.pulse_code = 2;
    otherwise,       S.pulse_code = 0;
end
switch cfg.fault
    case 'power_loss',  S.fault_code = 1;
    case 'frozen_hold', S.fault_code = 2;
    case 'inlet_open',  S.fault_code = 3;
    case 'stuck_all',   S.fault_code = 4;
    otherwise,          S.fault_code = 0;
end
S.stagger = p.exh_t_close - p.in_t_open;
floor_w = p.fill_floor;  if isnan(floor_w), floor_w = 0; end
if ~isnan(cfg.fill_at)
    S.t_fill_w = cfg.fill_at;
elseif S.pulse_code == 1
    S.t_fill_w = p.t_detect_bound;
elseif S.pulse_code == 2
    if ~isnan(p.t_fill_demand)
        S.t_fill_w = max(p.t_fill_demand, floor_w);               % ka_fill_timing (Rev 25)
    else
        [tl, ~] = ka_open_fill(p, 53, false, p.p_on_kPa, 0.6);    % slowest case (PR-15)
        S.t_fill_w = max(p.t_on - tl(end) - S.stagger, floor_w);  % G-5 floor
    end
else
    S.t_fill_w = inf;
end
if S.pulse_code == 1
    S.tau_stop = ka_ff(p, 'time', S.cap);
else
    S.tau_stop = ka_ff(p, 'time', p.p_on_kPa);
end
if isnan(cfg.stance), S.stance = p.T_stance; else, S.stance = cfg.stance; end
S.contact_ideal = strcmp(cfg.contact, 'ideal');
if isnan(cfg.insole_delay), ins = p.insole_delay; else, ins = cfg.insole_delay; end
S.sense_lag = ins + p.foot_filter;
S.n_foot = round(p.foot_Ts / dt);  S.k_next_foot = round(cfg.sample_phase / dt);
S.armed = true;  S.active = false;  S.w0 = NaN;  S.stage = 0;  S.last_stride = -1;
S.I = 0;  S.u = 0;  S.uff = 0;
S.k_en = 0;  S.per_start_k = 0;  S.chan = 0;  S.ended = true;  S.r = 0;
S.supply = true;  S.t_off_supply = inf;  S.tripped = false;  S.t_trip = 0;
S.pump_on = false;
S.n_ex_edges = 0;  S.last_e1o = false;  S.in_on_t = 0;  S.ex_pow_t = 0;
S.pump_time = 0;  S.pump_hi = 0;  S.pump_starts = 0;
S.ev = struct('detect', [], 'abort', [], 'fill', [], 'enable', [], 'offset', [], 'stride_pr', []);
end

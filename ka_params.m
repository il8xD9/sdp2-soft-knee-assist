function p = ka_params(pcase, n_in, window)
%KA_PARAMS  All inputs of the Rev 27 pneumatic model (Week 11) in one place.
%
%   p = ka_params            DESIGN SYSTEM: design point 20 kPa, ONE MHJ10,
%                            window option 2 (13-36 % stance, main)
%   p = ka_params(pc)        pc = 1: design point 20 kPa(g), trip 22.6 kPa(g)
%                            pc = 2: side case 27 kPa(g) (individual calibration
%                                    only, Basem O1 v10 B7), trip 29.6 kPa(g)
%   p = ka_params(pc, n)     n MHJ10 inlets in parallel (1 = Rev 27 system; 2 = comparison: meets N1 in window 2)
%   p = ka_params(pc, n, w)  w = 2: window option 2, 13-36 % stance, torque capped
%                                   at the patient's own moment (MAIN, owner D-2)
%                            w = 1: window option 1, 8.43-44 % stance (comparison)
%
%   Rev 27 = Rev 25a model updated with the Week 11 handover of Meshal and Basem
%   (13 Nov 2026):
%     - torque constant from the 3D virtual work on the CAD cavity (team T4):
%       k3D = 206 990 mm^3 -> 4.14 N m at 20 kPa, alpha 0.125 (CF-02);
%       the flat-section k2D = A_i (d_h + 28 mm) = 198 707 mm^3 is kept for comparison
%     - side case 27 kPa replaces 28 kPa (Basem O1 v10 B7 row 7; CF-01)
%     - Basem's window option 2 (main) and option 1 (comparison) with his
%       deficit, patient moment and knee angle tables (data\*.csv)
%     - swing squeeze 3.61 mL/deg (3D, CF-04) -> five MHE3 needed at the port (Rev 27 fits two: N4-2 not met)
%     - device of record 374.27 g (CAD v8, last v6; CF-03), used in the mass table
%     - pressure-relief valve (Circle Seal L500): FUTURE WORK. It is not part of
%       the Rev 27 system; p.relief_on stays false and no result counts on it.
%
%   HARDWARE IS NOT APPROVED. Every part below is a PROPOSED value until
%   Nawaf chooses the parts. Change the value on its line and re-run.
%   p.hw lists each part with its source; print it with ka_print_hardware(p).
%
%   Units: SI inside the model (Pa, s, kg, m^3); pressures for the
%   controller, set points and trips in kPa gauge.
%   Then call p = ka_prepare(p) before any run (or use ka_setup).

if nargin < 1 || isempty(pcase),  pcase = 1;  end   % design point 20 kPa
if nargin < 2 || isempty(n_in),   n_in = 1;   end   % Rev 27 system: ONE MHJ10 (owner decision; two = comparison)
if nargin < 3 || isempty(window), window = 2; end   % window option 2 (main)
if ~ismember(pcase, [1 2]),  error('ka_params: pressure case must be 1 (20 kPa) or 2 (27 kPa)'); end
if ~ismember(window, [1 2]), error('ka_params: window must be 1 or 2'); end
if n_in < 1 || n_in ~= round(n_in)
    error('ka_params: n_in must be a whole number of MHJ10 (1 for the design system)');
end

%% ---- physical constants ----
p.p_atm   = 101325;          % Pa
p.T0      = 293.15;          % K, room and supply temperature (20 C)
p.R       = 287.05;          % J/(kg K), air
p.gam     = 1.4;             % ratio of specific heats, air
p.p_anr   = 100e3;           % Pa, ISO 8778 ANR reference (100 kPa, 20 C)
p.rho_anr = p.p_anr / (p.R * p.T0);   % kg/m^3, density of one ANR litre
p.mu      = 1.81e-5;         % Pa s, air at 20 C
p.dt      = 10e-6;           % s, time step (pulse runs may use 20 us: Rev 16, 10-50 us agree within 0.04 ms)

%% ---- HARDWARE (PROPOSED, NOT APPROVED) ----
% Exhaust: Festo MHE3-MS1H-3/2O-1/8 (525167), normally open        [3]
%   200 l/min standard nominal flow; b not published -> 0.36 ASSUMED
%   (MHJ10 of the same Festo family, Rev 22 Section 3.2); C re-derived.
p = ka_exhaust_from_qn(p, 200, 0.36);    % exh_b 0.36, exh_C 0.821 l/(s bar)
p.exh_C_mult  = 1;                       % sensitivity factor on the exhaust flow
p.exh_t_close = 2.3e-3 * 1.1;            % s, powered -> shut (Festo 2.3 ms + 10 %)
p.exh_t_open  = 2.8e-3 * 1.1;            % s, released -> open (Festo 2.8 ms + 10 %)
p.ex_nmax     = 6;                       % exhaust tables for 1..6 valves
p.n_exh_sys   = 2;                       % Rev 27 complete system: TWO MHE3 at the bladder port (owner decision 14 Nov 2026; five needed for N4-2)
% Inlet: Festo MHJ10 HF/LP 567800, normally closed                  [4]
p.in_C_one    = 0.66e-8;                 % m^3/(s Pa) = 0.66 l/(s bar) per valve
p.n_in        = n_in;                    % Rev 27 system: ONE MHJ10 (owner decision); 2 = comparison
p.in_b        = 0.36;
p.in_t_open   = 1.0e-3;                  % s
p.in_t_close  = 0.5e-3;                  % s
% Receiver 1.5 L and pump KNF NMP 850.1.2 KPDC-B4 HP                [7], [8]
p.Vr            = 1.5e-3;                % m^3
p.pump_on_kPa   = 55;                    % pump switch on, kPa(g)
p.pump_off_kPa  = 70;                    % pump switch off, kPa(g)
p.pump_Qfree    = 15 / 60e3;             % m^3/s free flow
p.pump_pmax_kPa = 220;                   % kPa(g), flow on the line between the two points
p.pump_W        = 31.2;                  % W at 24 V
p.in_W          = 7.0;                   % W per MHJ10 while commanded
p.exh_W         = 6.5;                   % W per MHE3, switching (high-current) phase
p.exh_hold_W    = 1.6;                   % W, MHE3 holding power while powered shut
% Pressure sensors NXP MP3V5050GP (controller and trip)             [10]
p.sens_delay    = 1.0e-3;                % s, response time
p.sens_err_kPa  = 1.25;                  % kPa, +/- 2.5 % of 50 kPa span
p.ctrl_allow_kPa= 0.1;                   % kPa, control allowance in the trip rule
% Watchdog Maxim MAX6369, 10 ms setting                             [11]
p.t_wd          = 30e-3;                 % s, worst timeout (10-30 ms)
p.trip_extra    = 0;                     % s, extra trip delay (sensitivity)
p.supply_holdup = 0;                     % s, power-supply hold-up before the exhausts are released
% Foot sensor (Rev 23): two footswitches, 100 Hz low-pass, read at 1 kHz [27]-[29]
p.foot_Ts       = 1e-3;                  % s, controller ADC sampling
p.foot_filter   = 1.6e-3;                % s, group delay of the first-order 100 Hz filter
p.insole_delay  = 3e-3;                  % s, insole detection delay (Crea et al.: 3 mean, 7 max)
% Pressure-relief valve: FUTURE WORK in Rev 27 (owner decision, 13 Nov 2026).
% The code path is kept so the study can be resumed; it is OFF in every Rev 27 run.
p.relief_on     = false;
p.rel_crack_kPa = 22.1;                  % Circle Seal L500, 3.2 psig (future work)
p.rel_reseat_kPa= 20.0;                  % 2.9 psig
p.rel_p_kPa     = [22.1 24.3 27.6 33.1]; % kPa(g), 0 / 10 / 25 / 50 % over cracking
p.rel_q_scfm    = [0 1.32 3.1 5.41];     % SCFM, data sheet (L500-2MP, ESR 21625)

%% ---- bladder and tube (Meshal: CAD last v6, full asseymbly 07, hand calc v5) ----
p.V_cav    = 390.93e-6;                  % m^3, actuator-V8 route (a) (SH-P12)
p.tube_D   = 4e-3;                       % m, tupe-15 bore (PEN-6x1)
p.tube_L   = 0.080;                      % m
p.tube_K   = 1.5;                        % entrance 0.5 + exit 1.0 (Cengel & Cimbala Table 8-4)
p.tube_on  = true;                       % false = tube loss ignored (sensitivity)
p.V_tube   = pi/4 * p.tube_D^2 * p.tube_L;
p.V_mult   = 1;                          % sensitivity factor on the air volume
p.A_i      = 2136.6e-6;                  % m^2, inner section 62 x 40 mm stadium (SH-C02)
p.d_h      = 0.065;                      % m, hinge depth of record (band 0-0.080 m, no source)
p.d_off    = 0.028;                      % m, flat-section lever offset: t_pad 6 + t_w 2 + h_i/2 20 mm (SH-C03)
p.k3D      = 206990e-9;                  % m^3, 3D virtual work on the CAD cavity at d_h 65 (SH-C04, team T4)
p.k3D_band = [0 50 65 80; 67283 174750 206990 239230] ;   % d_h (mm); k3D (mm^3) (SH-C04)
p.k_basis  = '3D';                       % '3D' (Rev 27, governing) or '2D' (flat section, comparison)
p.swing_dVdeg = 3.613;                   % mL/deg = k3D x pi/180 (SH-C10; Rev 25 used the flat 4.03)
p.m_device = 374.27;                     % g, device on the leg, full asseymbly 07 (SH-P14, CF-03)

%% ---- gait and limits (Basem O1 v10 / O2 v3, 12 Nov 2026) ----
p.T_stride     = 1.175;                  % s
p.T_stance     = 0.705;                  % s
p.deadline_pct = 87.0;                   % % stance, knee 10.4 deg (B4), deflate deadline (613 ms)
p.def_peak     = 33.0;                   % N m, B1 deficit peak (design basis; 32.9675 unrounded)
p.def_peak_pct = 21.0;                   % % stance
p.rest_kPa     = 2.4;                    % B7 item 9
p.pain_kPa     = 28.9;                   % B7 item 8 (32.1 x 0.9)
p.vent_allow   = 0.303;                  % s, B7 item 10 (option 1 offset -> 613 ms)
p.knee_rate    = 261;                    % deg/s, fastest flexion in B4 (87 % stance to toe-off)
p.swing_flex_t = 0.141;                  % s of swing flexion (27.8 -> 65 deg)
p.knee0_t      = 0.042;                  % s, knee passes 0 deg (B4); D-B4-4
p.alpha_req    = 0.254;                  % requirement (8.39 N m), Basem B-D1
p.alpha_test   = 0.20;                   % test value (6.6 N m)

%% ---- controller (Rev 22: PI + feedforward + anti-windup; Rev 23 contact rules) ----
p.Ts        = 1e-3;                      % s, 1 kHz loop
p.Tpwm      = 5e-3;                      % s, 200 Hz PWM, one pulse per period
p.kp        = 0.30;                      % 1/kPa
p.ki        = 1.5;                       % 1/(kPa s)
p.use_ff    = true;
p.use_ff_release = true;                 % negative feedforward on one exhaust when the request falls
p.ff_release_gate = false;               % true: ... only once the bladder has caught up (tested in Rev 27, not adopted)
p.ff_gate_kPa     = 0.1;                 % kPa, "caught up" = within the control allowance
p.use_aw    = true;
p.clock_offset    = 5.6e-3;              % G-1: window clock zero at detection - 5.6 ms
p.fill_floor      = NaN;                 % G-5 floor; NaN = found by ka_fill_timing
p.t_fill_demand   = NaN;                 % demand-pulse fill command; NaN = found by ka_fill_timing
p.t_detect_bound  = 20e-3;               % bounding pulse: fill command at 20 ms

%% ---- pressure case and window ----
p = ka_set_option(p, pcase);
p = ka_set_window(p, window);

%% ---- register of parts (PROPOSED, NOT APPROVED) ----
p.hw = {
 'Inlet valve',     sprintf('%d x Festo MHJ10 HF/LP 567800, 2/2 NC', n_in),'in_C 0.66 l/(s bar) each, in_b 0.36, open 1.0 ms, close 0.5 ms', 'Festo data sheet 2023/05 [4]';
 'Exhaust valves',  '2 x Festo MHE3-MS1H-3/2O-1/8, NO, at the bladder port', 'exh_C 0.82 l/(s bar) at b 0.36 ASSUMED (200 l/min), shut 2.53 ms, open 3.08 ms', 'Festo 525167 [3]; b from MHJ10 [4]';
 'Bladder',         'actuator-V8 (route a, CAD last v6), Elastollan 1185A', 'V_cav 390.93 mL, A_i 2136.6 mm^2, k3D 206 990 mm^3 (0.207 N m/kPa)', 'Meshal hand calc v5 SH-C02..C04 [22]';
 'Tube',            'tupe-15, PEN-6x1', '4 mm bore x 80 mm, loss coefficient 1.5', 'CAD last v6 [23]; Cengel & Cimbala [12]';
 'Pump',            'KNF NMP 850.1.2 KPDC-B4 HP', 'pump_Qfree 15 l/min, pump_pmax 2.2 bar(g), 31.2 W', 'KNF data sheet and manual [7]';
 'Receiver',        '1.5 L vessel, switch 55/70 kPa(g)', 'Vr 1.5 L, pump_on 55, pump_off 70 kPa(g)', 'Xavier 2022 Sec. 3 [8]';
 'Pressure sensors','2 x NXP MP3V5050GP', 'sens_delay 1.0 ms, sens_err 1.25 kPa', 'NXP data sheet Rev 1.2 [10]';
 'Watchdog',        'Maxim MAX6369, 10 ms setting', 't_wd 30 ms (worst of 10-30 ms)', 'Maxim 19-1676 Rev 9 [11]';
 'Foot sensor',     '2 footswitches (heel, 1st metatarsal head)', '1 kHz, 100 Hz filter 1.6 ms, insole delay 0-7 ms, clock at detection - 5.6 ms', 'Taborri et al. 2016 [27]-[29]';
 'Relief valve',    'FUTURE WORK (not fitted in Rev 27)', 'Circle Seal L500 at 22.1 kPa studied in Rev 24e/25', 'Section 13 of the Rev 27 report'};
p.hw_status = sprintf('PROPOSED, NOT APPROVED - Rev 27 (Week 11 handover), %s, %s, %d MHJ10', p.opt_name, p.win_name, n_in);
end

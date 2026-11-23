function R = run27_n5(make_figs)
%RUN27_N5  N5 fail-safe venting, Rev 27 (no pressure-relief valve: future work).
%   Every fault starts at the set point; faults that keep filling are also started
%   from 21 pressures between 0 and the most the trip allows. Worst of both heat
%   cases, receiver 70 kPa(g). Trip = set point + 2.6 kPa (22.6 / 29.6).
%   Close-out basis: one MHE3 through the tube. Complete system: two MHE3 at the port.
%   Figures 6 (faults) and 7 (FS-3 against the trip setting).
if nargin < 1, make_figs = true; end
fprintf('\n===== N5 fail-safe venting =====\n');
t0 = tic;
base  = ka_setup(1, 1, 2, 'timing', false);      % Rev 27 system: one MHJ10
base2 = ka_setup(1, 2, 2, 'timing', false);      % comparison: two MHJ10
R = struct();
bases = {1, 0, 'cb', 'close-out basis (one MHE3 through the tube)';
         2, 1, 'cs', 'complete system (two MHE3 at the port)'};

%% ---- fault table, both exhaust arrangements ----
for pc = 1:2
    p = ka_case(base, pc, 2);  lim = p.limit_kPa;  o = p.opt_short;
    trip = p.trip_kPa;  p0s = linspace(0, min(lim, trip + p.sens_err_kPa), 21);
    for b = 1:2
        ne = bases{b,1};  ap = bases{b,2};  ob = [o '.' bases{b,3}];  nm = bases{b,4};
        [v, pk] = fault_worst(p, {'fault','power_loss','init','filling'}, lim, ne, ap);
        ka_report('add', ['N5.pl.' ob],  sprintf('%s, %s: power loss, vented', p.opt_name, nm), v, NaN, 'ms');
        ka_report('add', ['N5.plp.' ob], sprintf('%s, %s: power loss, peak', p.opt_name, nm), pk, NaN, 'kPa');
        v = fault_worst(p, {'fault','frozen_hold','init','holding','watchdog',true}, lim, ne, ap);
        ka_report('add', ['N5.wd.' ob],  sprintf('%s, %s: frozen in hold + watchdog 30 ms, vented', p.opt_name, nm), v, NaN, 'ms');
        [v, pk] = fault_worst(p, {'fault','inlet_open','init','filling','watchdog',true}, linspace(0, lim, 21), ne, ap);
        ka_report('add', ['N5.A.' ob],   sprintf('%s, %s: inlet held open, watchdog only, vented', p.opt_name, nm), v, NaN, 'ms');
        ka_report('add', ['N5.Ap.' ob],  sprintf('%s, %s: inlet held open, watchdog only, peak', p.opt_name, nm), pk, NaN, 'kPa');
        tr = {'fault','inlet_open','init','filling','watchdog',true,'trip_kPa',trip,'trip_err_kPa',p.sens_err_kPa};
        [v, pk] = fault_worst(p, tr, p0s, ne, ap);
        ka_report('add', ['N5.B.' ob],   sprintf('%s, %s: inlet held open + trip %.1f, vented', p.opt_name, nm, trip), v, NaN, 'ms');
        ka_report('add', ['N5.Bp.' ob],  sprintf('%s, %s: inlet held open + trip, peak (FS-3 < 28.9)', p.opt_name, nm), pk, pick(pc, 24.3, 31.3), 'kPa');
        R.Bp(pc, b) = pk;
    end
    p2 = ka_case(base2, pc, 2);
    [~, pk] = fault_worst(p2, {'fault','inlet_open','init','filling','watchdog',true,'trip_kPa',trip,'trip_err_kPa',p.sens_err_kPa}, p0s, 2, 1);
    ka_report('add', ['N5.Bp.in2.' o], sprintf('%s, TWO MHJ10 (comparison), complete system: inlets held open + trip, peak', p.opt_name), pk, pick(pc, 24.8, 31.8), 'kPa');
    fprintf('  [%.0f s]\n', toc(t0));
end

%% ---- limits on the protection hardware (close-out basis, as Rev 25 Table 9) ----
for pc = 1:2
    p = ka_case(base, pc, 2);  lim = p.limit_kPa;  o = p.opt_short;
    f = @(x) fault_worst(setf(p, 'supply_holdup', x), {'fault','power_loss','init','filling','t_end',0.7}, lim, 1, 0) - 303;
    ka_report('add', ['L.rel.' o], sprintf('%s: longest exhaust opening delay incl. hold-up (FS-1)', p.opt_name), (bisect(f, 0, 0.3) + p.exh_t_open) * 1e3, NaN, 'ms');
    f = @(x) fault_worst(setf(p, 't_wd', x), {'fault','frozen_hold','init','holding','watchdog',true,'t_end',0.7}, lim, 1, 0) - 303;
    ka_report('add', ['L.wdh.' o], sprintf('%s: longest watchdog time, frozen in hold (FS-2)', p.opt_name), bisect(f, 0, 0.3) * 1e3, NaN, 'ms');
    g = @(x) trip_peak(setf(p, 'trip_extra', x), p.trip_kPa) - p.pain_kPa;
    if g(0) >= 0
        td = NaN;  fprintf('  %s: the design trip fails FS-3 even with no extra delay\n', p.opt_name);
    else
        td = bisect(g, 0, 0.05) * 1e3 + p.sens_delay * 1e3;
    end
    ka_report('add', ['L.trip.' o], sprintf('%s: longest trip delay with the design trip (FS-3; NaN = fails at 0)', p.opt_name), td, NaN, 'ms');
    fprintf('  [%.0f s]\n', toc(t0));
end
p = ka_case(base, 1, 2);
h = @(s) trip_peak(p, s) - p.pain_kPa;
hi = bisect(h, 15, 28.9);
ka_report('add', 'L.trip.max', 'Highest trip setting that meets FS-3, one MHJ10 (sensor error included)', hi, 27.2, 'kPa');
ka_report('add', 'L.sp.max', 'Highest set point that meets FS-3 = highest trip - 2.6 (one MHJ10)', hi - 2 * p.sens_err_kPa - p.ctrl_allow_kPa, 24.6, 'kPa');
p1c = ka_case(base2, 1, 2);  hi1 = bisect(@(s) trip_peak(p1c, s) - p1c.pain_kPa, 15, 28.9);
ka_report('add', 'L.trip.max.in2', 'Highest trip setting that meets FS-3, TWO MHJ10', hi1, 26.7, 'kPa');
ka_report('add', 'L.sp.max.in2', 'Highest set point that meets FS-3, TWO MHJ10', hi1 - 2.6, 24.1, 'kPa');
R.trip_max = hi;

%% ---- FS-3 peak against the trip setting (figure 7) ----
trips = 20:1:31;
R.trips = trips;  R.tp1 = zeros(size(trips));  R.tp2 = R.tp1;
p2 = ka_case(base2, 1, 2);
for i = 1:numel(trips)
    R.tp1(i) = trip_peak(p, trips(i));
    R.tp2(i) = trip_peak(p2, trips(i));
end
fprintf('  FS-3 curve done [%.0f s]\n', toc(t0));

%% ---- sensitivity (fault at the set point, design trip, close-out basis) ----
rows = {'base', 'Base case (b 0.36, C 0.82)',  {};
        'b0',   'Exhaust b 0 (C 1.00)',          {'exh_b', 0};
        'b528', 'Exhaust b 0.528 (C 0.72)',      {'exh_b', 0.528};
        'c07',  'Exhaust flow x 0.7',            {'exh_C_mult', 0.7};
        'v15',  'Air volume x 1.5',              {'V_mult', 1.5};
        'rel20','Exhaust opening delay 20 ms',   {'exh_t_open', 20e-3};
        'tube0','Tube loss ignored',             {'tube_on', false};
        'r150', 'Receiver 150 kPa(g)',           {};
        'trip5','Trip delay +4 ms',              {'trip_extra', 4e-3}};
for i = 1:size(rows, 1)
    if isempty(rows{i,3}), q = base; else, q = ka_setup(1, 1, 2, 'timing', false, rows{i,3}{:}); end
    pr = 70;  if strcmp(rows{i,1}, 'r150'), pr = 150; end
    for pc = 1:2
        p = ka_case(q, pc, 2);  lim = p.limit_kPa;
        v = fault_worst(p, {'fault','power_loss','init','filling','pr_kPa',pr}, lim, 1, 0);
        [~, pk] = fault_worst(p, {'fault','inlet_open','init','filling','watchdog',true, ...
                     'trip_kPa',p.trip_kPa,'trip_err_kPa',p.sens_err_kPa,'pr_kPa',pr}, min(lim, p.trip_kPa + p.sens_err_kPa), 1, 0);
        ka_report('add', sprintf('S.%s.pl.%s', rows{i,1}, p.opt_short), sprintf('%s, %s: power loss vented (close-out basis)', rows{i,2}, p.opt_short), v, NaN, 'ms');
        ka_report('add', sprintf('S.%s.tp.%s', rows{i,1}, p.opt_short), sprintf('%s, %s: inlet fault + trip, peak', rows{i,2}, p.opt_short), pk, NaN, 'kPa');
    end
end
fprintf('  sensitivity done [%.0f s]\n', toc(t0));

%% ---- inlet stuck open mechanically, supply cut (exhausts open): steady pressure ----
p = ka_case(base, 1, 2);  p2 = ka_case(base2, 1, 2);
prs = [70 100 150];
for j = 1:3
    ka_report('add', sprintf('SO.%d.n2', prs(j)), sprintf('One MHJ10 stuck open, receiver %d kPa(g), two MHE3 at the port open: settles at', prs(j)), ka_stuck_open(p, prs(j), 2, true), NaN, 'kPa');
    ka_report('add', sprintf('SO.%d.n5', prs(j)), sprintf('Same, five MHE3 at the port (Rev 26 arrangement)', prs(j)), ka_stuck_open(p, prs(j), 5, true), NaN, 'kPa');
    ka_report('add', sprintf('SO.%d.n2.in2', prs(j)), sprintf('Two MHJ10 stuck open, receiver %d kPa(g), two MHE3 open', prs(j)), ka_stuck_open(p2, prs(j), 2, true), NaN, 'kPa');
end

%% ---- figures ----
if make_figs
    C = ka_colours();
    figure('Name', 'N5 faults', 'Color', 'w', 'Position', [60 60 1150 430]);
    for pc = 1:2
        p = ka_case(base, pc, 2);
        subplot(1, 2, pc);  hold on;  grid on;
        sp = {{'fault','power_loss','init','filling','adiabatic',false}, ...
              {'fault','frozen_hold','init','holding','watchdog',true,'adiabatic',false}, ...
              {'fault','inlet_open','init','filling','watchdog',true,'adiabatic',true}, ...
              {'fault','inlet_open','init','filling','watchdog',true,'adiabatic',true,'trip_kPa',p.trip_kPa,'trip_err_kPa',p.sens_err_kPa}, ...
              {'fault','power_loss','init','filling','adiabatic',false,'n_exh',2,'exh_at_port',true}};
        nm = {'power loss', 'frozen in hold, watchdog 30 ms', 'inlet held open, watchdog only', ...
              sprintf('inlet held open, trip %.1f kPa', p.trip_kPa), 'power loss, two MHE3 at the port'};
        st = {'-', '-', '--', '-', ':'};  col = {C.s1, C.ink, C.s3, C.s2, C.s1};
        for j = 1:5
            r = ka_simulate(p, ka_default_cfg('pulse','none','p0_kPa',p.limit_kPa,'pr_kPa',70,'t_end',0.45, sp{j}{:}));
            plot(r.log.t*1e3, r.log.p, st{j}, 'Color', col{j}, 'LineWidth', 1.6, 'DisplayName', nm{j});
        end
        yline(p.rest_kPa, ':k', 'rest 2.4 kPa', 'HandleVisibility', 'off');
        yline(p.pain_kPa, ':r', 'pain onset 28.9 kPa', 'HandleVisibility', 'off');
        xlabel('time after the fault (ms)');  ylabel('bladder (kPa(g))');  ylim([0 42]);
        title(sprintf('%s: fault at %g kPa, one MHE3 through the tube', p.opt_name, p.limit_kPa));
        if pc == 1, legend('Location', 'northeast'); end
    end
    ka_savefig('fig06_n5_faults');

    figure('Name', 'FS-3 against the trip', 'Color', 'w', 'Position', [60 60 1000 420]);  hold on;  grid on;
    plot(R.trips, R.tp1, 'o-', 'Color', C.s1, 'LineWidth', 1.8, 'DisplayName', 'one MHJ10 (Rev 27 system)');
    plot(R.trips, R.tp2, 's--', 'Color', C.ink, 'LineWidth', 1.4, 'DisplayName', 'two MHJ10 (comparison)');
    yline(28.9, '-r', 'pain onset 28.9 kPa (FS-3)', 'HandleVisibility', 'off');
    xline(22.6, ':', 'design trip 22.6 (20 kPa)', 'Color', C.s1, 'HandleVisibility', 'off');
    xline(29.6, ':', 'design trip 29.6 (27 kPa)', 'Color', C.s2, 'HandleVisibility', 'off');
    xline(R.trip_max, '--', sprintf('highest trip %.1f kPa (one MHJ10) -> set point %.1f kPa', R.trip_max, R.trip_max - 2.6), 'Color', C.s3, 'HandleVisibility', 'off');
    xlabel('trip setting (kPa(g))');  ylabel('peak with the inlet held open (kPa(g))');  legend('Location', 'northwest');
    title('FS-3: inlet held open, fault starts at trip + 1.25 kPa, no relief valve (future work)');
    ka_savefig('fig07_fs3_trip_peak');
end
fprintf('N5 done in %.1f min\n', toc(t0) / 60);
end

%% =====================================================================
function [v, pk] = fault_worst(p, spec, p0s, n_exh, at_port)
v = 0;  pk = -inf;
for p0 = p0s(:)'
    for adi = [false true]
        c = ka_default_cfg('pulse','none','pr_kPa',70,'t_end',0.6,'n_exh',n_exh, ...
                           'exh_at_port',logical(at_port),'p0_kPa',p0,'adiabatic',adi, ...
                           'stop_vented',true, spec{:});
        m = ka_metrics_fault(p, ka_simulate(p, c));
        v = max(v, m.vented_ms);  pk = max(pk, m.peak_kPa);
    end
end
end
function pk = trip_peak(p, trip)
[~, pk] = fault_worst(p, {'fault','inlet_open','init','filling','watchdog',true,'trip_kPa',trip, ...
                          'trip_err_kPa',p.sens_err_kPa,'t_end',0.3}, trip + p.sens_err_kPa, 1, 0);
end
function q = setf(q, f, v), q.(f) = v; end
function x = bisect(f, a, b)
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
function v = pick(i, a, b), if i == 1, v = a; else, v = b; end, end

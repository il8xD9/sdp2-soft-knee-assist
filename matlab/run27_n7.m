function R = run27_n7(P, make_figs)
%RUN27_N7  N7 air supply over 40 strides, pump duty and electrical power.
%   P = R.p from run27_n1_n4. Receiver 1.5 L starting at 70 kPa(g); pump on at 55,
%   off at 70 kPa(g). Complete system (two MHE3 at the port), room temperature.
%   Figure 13 (receiver over 40 strides).
if nargin < 1 || isempty(P), P = ka_get_P(); end   % allows running with no input
if nargin < 2, make_figs = true; end
fprintf('\n===== N7 air supply, 40 strides =====\n');
t0 = tic;
N = 40;
base = ka_setup(1, 1, 2, 'timing', false);      % design system: one MHJ10
Ttot = N * base.T_stride;   % (stray 'D' removed)
R = struct();
runs = {};   % {label, p, pulse, Vr}
runs(end+1, :) = {'bound.P20', ka_case(base, 1, 2), 'bounding', 1.5};
runs(end+1, :) = {'bound.P27', ka_case(base, 2, 2), 'bounding', 1.5};
runs(end+1, :) = {'dem.P20.W2.in2', P{2,1,2}, 'demand', 1.5};
runs(end+1, :) = {'dem.P27.W2.in2', P{2,2,2}, 'demand', 1.5};
runs(end+1, :) = {'dem.P20.W2.in1', P{1,1,2}, 'demand', 1.5};
runs(end+1, :) = {'dem.P27.W2.in1', P{1,2,2}, 'demand', 1.5};
runs(end+1, :) = {'dem.P20.W1.in1', P{1,1,1}, 'demand', 1.5};
runs(end+1, :) = {'dem.P27.W2.in1.3L', P{1,2,2}, 'demand', 3.0};
hand_air = struct('P20', 78.4, 'P27', 105.8);
for i = 1:size(runs, 1)
    lab = runs{i,1};  p = runs{i,2};  p.Vr = runs{i,4} * 1e-3;
    c = ka_default_cfg('pulse', runs{i,3}, 'n_exh', 2, 'exh_at_port', true, 'adiabatic', false, ...
                       'pr_kPa', 70, 'receiver_dynamic', true, 'n_strides', N, 'log_every', 100);
    r = ka_simulate(p, c);
    air = r.air_mL / N;
    last = r.log.t >= (N-1) * p.T_stride;
    nm = sprintf('%s, %s pulse, %d MHJ10, %.1f L', ifelse(strcmp(runs{i,3}, 'bounding'), p.opt_name, [p.win_name ', ' p.opt_name]), runs{i,3}, p.n_in, runs{i,4});
    if strcmp(runs{i,3}, 'bounding'), ha = hand_air.(p.opt_short); else, ha = NaN; end
    ka_report('add', ['N7.air.' lab],  [nm ': air per stride (ANR)'], air, ha, 'mL');
    ka_report('add', ['N7.drop.' lab], [nm ': receiver drop per pulse'], air * 1e-6 * p.p_anr / p.Vr / 1e3, ifelse(isnan(ha), NaN, ha * 100 / (runs{i,4} * 1e3)), 'kPa');
    ka_report('add', ['N7.lo.' lab],   [nm ': receiver lowest (MHJ10 needs >= 50)'], r.pr_min, NaN, 'kPa(g)');
    ka_report('add', ['N7.start.' lab],[nm ': receiver at the start of a pulse, lowest'], min(r.ev.stride_pr), NaN, 'kPa(g)');
    ka_report('add', ['N7.pk40.' lab], [nm ': peak at stride 40 (% of the set point)'], max(r.log.p(last)) / p.cap_kPa * 100, NaN, '%');
    ka_report('add', ['N7.pump.' lab], [nm ': pump running'], r.pump_time / Ttot * 100, NaN, '%');
    ka_report('add', ['N7.p07.' lab],  [nm ': pump time above 0.7 bar(g)'], r.pump_hi / max(r.pump_time, eps) * 100, 0, '%');
    ka_report('add', ['N7.starts.' lab], [nm ': pump starts per minute'], r.pump_starts / Ttot * 60, NaN, '/min');
    Pavg = p.pump_W * r.pump_time / Ttot + p.n_in * p.in_W * r.in_on_t / Ttot + p.exh_hold_W * r.ex_pow_t / Ttot;
    ka_report('add', ['N7.Pavg.' lab], [nm ': average electrical power'], Pavg, NaN, 'W');
    ka_report('add', ['N7.run.' lab],  [nm ': runtime on 63 Wh (90 % efficiency)'], 63 * 0.9 / Pavg, NaN, 'h');
    R.run.(strrep(lab, '.', '_')) = r;
    fprintf('  %s [%.0f s]\n', lab, toc(t0));
end
tau = base.Vr * base.pump_pmax_kPa * 1e3 / (base.p_anr * base.pump_Qfree);
ka_report('add', 'N7.charge', 'Receiver 1.5 L: charge from 0 to 70 kPa(g) on the pump line', -tau * log(1 - 70 / base.pump_pmax_kPa), 5.06, 's');
ka_report('add', 'P.peak.sys', 'Peak electrical power: pump + one MHJ10 + two MHE3 switching (design system)', base.pump_W + 1*base.in_W + 2*base.exh_W, 51.2, 'W');
ka_report('add', 'P.peak.in2', 'Peak electrical power: pump + two MHJ10 + two MHE3', base.pump_W + 2*base.in_W + 2*base.exh_W, 58.2, 'W');
ka_report('add', 'P.peak.26', 'Peak electrical power, comparison: one MHJ10 + five MHE3', base.pump_W + 1*base.in_W + 5*base.exh_W, 70.7, 'W');

%% ---- figure ----
if make_figs
    C = ka_colours();
    r = R.run.dem_P27_W2_in1;  r0 = R.run.dem_P20_W2_in1;
    figure('Name', 'Receiver over 40 strides', 'Color', 'w', 'Position', [60 60 1150 500]);
    subplot(3, 1, [1 2]);  hold on;  grid on;
    plot(r0.log.t, r0.log.pr, 'Color', C.s1, 'LineWidth', 1.4, 'DisplayName', 'window 2, 20 kPa');
    plot(r.log.t, r.log.pr, 'Color', C.s2, 'LineWidth', 1.4, 'DisplayName', 'window 2, 27 kPa');
    yline(70, '--', 'pump off 70', 'Color', [0.5 0.5 0.5], 'HandleVisibility', 'off');
    yline(55, '--', 'pump on 55', 'Color', [0.5 0.5 0.5], 'HandleVisibility', 'off');
    yline(50, ':r', 'MHJ10 inlet minimum 50 kPa(g)', 'HandleVisibility', 'off');
    ylim([45 75]);  ylabel('receiver (kPa(g))');  legend('Location', 'southeast');
    title('Receiver 1.5 L over 40 strides: demand pulse at the design \alpha, one MHJ10, two MHE3');
    subplot(3, 1, 3);  hold on;
    area(r.log.t, r.log.pump, 'FaceColor', C.s2, 'EdgeColor', 'none', 'FaceAlpha', 0.6);
    ylim([0 1.2]);  ylabel('pump on (27 kPa)');  xlabel('time (s)');  grid on;
    ka_savefig('fig13_receiver_40_strides');
end
fprintf('N7 done in %.1f min\n', toc(t0) / 60);
end
function v = ifelse(c, a, b), if c, v = a; else, v = b; end, end

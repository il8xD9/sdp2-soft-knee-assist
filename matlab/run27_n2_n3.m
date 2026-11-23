function R = run27_n2_n3(make_figs)
%RUN27_N2_N3  Controller, set point and exposure (N2, N3).
%   Bounding pulse: fastest fill to the set point (fill command at 20 ms), hold to
%   the window offset, vent. Four cases: room temperature / no heat exchange x
%   receiver 53 / 70 kPa(g); worst kept. Close-out basis: one MHJ10 (system), one MHE3
%   through the tube. Complete system: two MHE3 at the port.
%   Figures 4 (fill at the slowest case) and 5 (bounding pulse over a stride).
if nargin < 1, make_figs = true; end
fprintf('\n===== N2 / N3: controller, set point, exposure =====\n');
base = ka_setup(1, 1, 2, 'timing', false);      % design system: one MHJ10
cases = [0 53; 0 70; 1 53; 1 70];
R = struct();
for pc = 1:2
    p = ka_case(base, pc, 2);  o = p.opt_short;
    M = run_cases(p, cases, {'pulse','bounding','t_end',0.40});
    f53 = max([M([1 3]).fill2_ms]);  f70 = max([M([2 4]).fill2_ms]);  pk = max([M.peak_kPa]);
    ka_report('add', ['T.over.' o],   sprintf('%s: worst overshoot above the set point (level 0.1)', p.opt_name), max([M.over_kPa]), NaN, 'kPa');
    ka_report('add', ['T.fill53.' o], sprintf('%s: fill command to 2 %% of the set point, receiver 53', p.opt_name), f53, NaN, 'ms');
    ka_report('add', ['T.fill70.' o], sprintf('%s: same, receiver 70', p.opt_name), f70, NaN, 'ms');
    ka_report('add', ['T.merr.' o],   sprintf('%s: mean error over the hold (worst)', p.opt_name), max([M.mean_err_kPa]), NaN, 'kPa');
    ka_report('add', ['T.pulses.' o], sprintf('%s: inlet openings per stride (most)', p.opt_name), max([M.inlet_pulses]), NaN, '-');
    q = p;  q.use_aw = false;  Mq = run_cases(q, cases, {'pulse','bounding','t_end',0.40});
    ka_report('add', ['T.noAW.peak.' o], sprintf('%s: without anti-windup, peak', p.opt_name), max([Mq.peak_kPa]), NaN, 'kPa');
    ka_report('add', ['T.noAW.fill.' o], sprintf('%s: without anti-windup, fill to 2 %%', p.opt_name), max([Mq.fill2_ms]), NaN, 'ms');
    q = p;  q.use_ff = false;  Mq = run_cases(q, cases, {'pulse','bounding','t_end',0.40});
    ka_report('add', ['T.noFF.peak.' o], sprintf('%s: without feedforward, peak', p.opt_name), max([Mq.peak_kPa]), NaN, 'kPa');
    ka_report('add', ['T.noFF.fill.' o], sprintf('%s: without feedforward, fill to 2 %%', p.opt_name), max([Mq.fill2_ms]), NaN, 'ms');
    ka_report('add', ['N2.true.' o], sprintf('%s: highest true pressure = peak + 1.25', p.opt_name), pk + p.sens_err_kPa, p.cap_kPa + 1.25, 'kPa');
    ka_report('add', ['N2.low.' o],  sprintf('%s: lowest true pressure at the hold', p.opt_name), p.cap_kPa - max([M.mean_err_kPa]) - p.sens_err_kPa, NaN, 'kPa');
    ka_report('add', ['N2.trip.' o], sprintf('%s: trip setting = set point + 2 x 1.25 + 0.1', p.opt_name), p.trip_kPa, pick(pc, 22.6, 29.6), 'kPa');
    % N3 exposure over one stride, both windows, single-exhaust basis and complete system
    for w = [2 1]
        pw = ka_case(base, pc, w);  ow = [o '.' pw.win_short];
        M = run_cases(pw, cases, {'pulse','bounding','t_end',pw.T_stride});
        ka_report('add', ['N3.above.' ow], sprintf('%s, %s, single-exhaust basis: time above 2.4 kPa per stride', pw.opt_name, pw.win_name), max([M.above_ms]), NaN, 'ms');
        ka_report('add', ['N3.defl.' ow],  sprintf('%s, %s, single-exhaust basis: vented after the offset', pw.opt_name, pw.win_name), max([M.deflated_ms]), NaN, 'ms');
        M2 = run_cases(pw, cases, {'pulse','bounding','n_exh',2,'exh_at_port',true,'t_end',pw.T_stride});
        ka_report('add', ['N3.above2.' ow], sprintf('%s, %s, two MHE3 at the port: time above 2.4 kPa', pw.opt_name, pw.win_name), max([M2.above_ms]), NaN, 'ms');
        ka_report('add', ['N3.defl2.' ow],  sprintf('%s, %s, two MHE3 at the port: vented after the offset', pw.opt_name, pw.win_name), max([M2.deflated_ms]), NaN, 'ms');
        ka_report('add', ['N3.pon2.' ow],   sprintf('%s, %s, bounding pulse: pressure at the onset (worst)', pw.opt_name, pw.win_name), min([M2.p_onset_kPa]), NaN, 'kPa');
        M5 = run_cases(pw, cases, {'pulse','bounding','n_exh',5,'exh_at_port',true,'t_end',pw.T_stride});
        ka_report('add', ['N3.above5.' ow], sprintf('%s, %s, five MHE3 at the port (comparison): time above 2.4 kPa', pw.opt_name, pw.win_name), max([M5.above_ms]), NaN, 'ms');
        ka_report('add', ['N3.defl5.' ow],  sprintf('%s, %s, five MHE3 at the port (comparison): vented after the offset', pw.opt_name, pw.win_name), max([M5.deflated_ms]), NaN, 'ms');
    end
end

%% ---- figures ----
if make_figs
    C = ka_colours();
    figure('Name', 'Fill at the slowest case', 'Color', 'w', 'Position', [60 60 1150 650]);
    for pc = 1:2
        p = ka_case(base, pc, 2);
        c = ka_default_cfg('pulse','bounding','adiabatic',false,'pr_kPa',53,'t_end',0.26);
        q2 = p;  q2.use_aw = false;  q3 = p;  q3.use_ff = false;
        r1 = ka_simulate(p, c);  r2 = ka_simulate(q2, c);  r3 = ka_simulate(q3, c);
        subplot(3, 2, [pc pc+2]);  hold on;  grid on;
        plot(r1.log.t*1e3, r1.log.r, ':', 'Color', [0.5 0.5 0.5], 'LineWidth', 1.2);
        plot(r2.log.t*1e3, r2.log.p, 'Color', C.s3, 'LineWidth', 1.6);
        plot(r3.log.t*1e3, r3.log.p, '--', 'Color', C.s2, 'LineWidth', 1.6);
        plot(r1.log.t*1e3, r1.log.p, 'Color', C.s1, 'LineWidth', 2);
        yline(p.cap_kPa, '-', sprintf('set point %g kPa', p.cap_kPa), 'Color', C.ink);
        yline(p.pain_kPa, ':r', 'pain onset 28.9');
        xlim([15 250]);  ylim([0 31]);  ylabel('bladder (kPa(g))');
        title(sprintf('%s: receiver 53 kPa(g), room temperature, one MHJ10', p.opt_name));
        legend('reference', 'without anti-windup', 'without feedforward', 'PI + FF + anti-windup', 'Location', 'southeast');
        subplot(3, 2, pc + 4);  hold on;  grid on;
        plot(r1.log.t*1e3, r1.log.u, 'Color', C.s1);  plot(r1.log.t*1e3, r1.log.uff, '--', 'Color', [0.5 0.5 0.5]);
        xlim([15 250]);  ylim([-0.2 1.1]);  xlabel('time after contact (ms)');  ylabel('duty');  legend('u', 'u_{ff}');
    end
    ka_savefig('fig04_fill_slowest_case');

    figure('Name', 'Bounding pulse', 'Color', 'w', 'Position', [60 60 1150 420]);  hold on;  grid on;
    patch([91.65 253.8 253.8 91.65], [0 0 33 33], [0.99 0.93 0.88], 'EdgeColor', 'none', 'HandleVisibility', 'off');
    col = {C.s1, C.s2};
    for pc = 1:2
        p = ka_case(base, pc, 2);
        r = ka_simulate(p, ka_default_cfg('pulse','bounding','adiabatic',false,'pr_kPa',53,'t_end',p.T_stride));
        r5 = ka_simulate(p, ka_default_cfg('pulse','bounding','adiabatic',false,'pr_kPa',53,'n_exh',2,'exh_at_port',true,'t_end',p.T_stride));
        plot(r.log.t*1e3, r.log.p, 'Color', col{pc}, 'LineWidth', 1.8, 'DisplayName', sprintf('%s: one MHE3 through the tube (single-exhaust basis)', p.opt_name));
        plot(r5.log.t*1e3, r5.log.p, '--', 'Color', col{pc}, 'LineWidth', 1.5, 'DisplayName', sprintf('%s: two MHE3 at the port (system)', p.opt_name));
        yline(p.trip_kPa, ':', sprintf('trip %.1f', p.trip_kPa), 'Color', col{pc}, 'HandleVisibility', 'off');
    end
    yline(base.pain_kPa, ':r', 'pain onset 28.9', 'HandleVisibility', 'off');
    yline(base.rest_kPa, ':k', 'rest 2.4 kPa', 'HandleVisibility', 'off');
    xline(base.t_deadline * 1e3, '-.r', '613 ms: knee 10.4 deg', 'HandleVisibility', 'off');
    xlim([0 1175]);  ylim([0 33]);  xlabel('time after contact (ms)');  ylabel('bladder (kPa(g))');
    title('Bounding pulse over one stride, window 2 (shaded), room temperature, receiver 53 kPa(g), one MHJ10');
    legend('Location', 'east');
    ka_savefig('fig05_bounding_pulse');
end
end

function M = run_cases(p, cases, spec)
for i = 1:size(cases, 1)
    c = ka_default_cfg('adiabatic', logical(cases(i,1)), 'pr_kPa', cases(i,2), spec{:});
    m = ka_metrics_pulse(p, ka_simulate(p, c));
    M(i) = m; %#ok<AGROW>
end
end
function v = pick(i, a, b), if i == 1, v = a; else, v = b; end, end

function R = run27_n1_n4(make_figs)
%RUN27_N1_N4  N1 pressure at the onset and N4 free knee flexion at the design alpha, Rev 27.
%   Demand-following pulse: rise to the onset demand, then MIN(tau_req / k, set point)
%   on Basem's window (window 2: capped at the patient's moment). Fill command and
%   G-5 floor from ka_fill_timing. Complete system: two MHE3 at the bladder port.
%   Cases: window 2 (main) and window 1 (comparison) x 20 / 27 kPa x one / two MHJ10;
%   each with the clock -4 / 0 / +4 ms and four heat / receiver cases.
%   Figures 8 (window 2 pulses), 9 (window 1 pulses), 10 (knee angle), 11 (torque).
if nargin < 1, make_figs = true; end
fprintf('\n===== N1 / N4 at the design alpha =====\n');
t0 = tic;
cases = [0 53; 0 70; 1 53; 1 70];
errs = [-4 0 4] / 1e3;
spec = {'pulse','demand','n_exh',2,'exh_at_port',true,'t_end',0.66};
R = struct();
for nin = 1:2
    base = ka_setup(1, nin, 2, 'timing', false);
    for w = [2 1]
        for pc = 1:2
            p = ka_case(base, pc, w);
            [p.fill_floor, p.t_fill_demand, scan] = ka_fill_timing(p);
            o = sprintf('%s.%s.in%d', p.opt_short, p.win_short, nin);
            nm = sprintf('%s, %s, %d MHJ10', p.win_name, p.opt_name, nin);
            fprintf('%s: alpha %.4f, onset demand %.2f kPa, G-5 floor %.2f ms, fill %.2f ms  [%.0f s]\n', ...
                    nm, p.alpha, p.p_on_kPa, p.fill_floor*1e3, p.t_fill_demand*1e3, toc(t0));
            clear M
            for e = 1:numel(errs)
                for i = 1:size(cases, 1)
                    c = ka_default_cfg('adiabatic', logical(cases(i,1)), 'pr_kPa', cases(i,2), 'clock_err', errs(e), spec{:});
                    M(e, i) = ka_metrics_demand(p, ka_simulate(p, c)); %#ok<AGROW>
                end
            end
            M0 = M(2, :);  Me = M(1, :);
            [tl, ~] = ka_open_fill(p, 53, false, p.p_on_kPa, 0.6);
            ka_report('add', ['N1.floor.' o], [nm ': G-5 floor (window clock)'], p.fill_floor*1e3, NaN, 'ms');
            ka_report('add', ['N1.fill.' o],  [nm ': fill command (window clock)'], p.t_fill_demand*1e3, NaN, 'ms');
            ka_report('add', ['N1.lead.' o],  [nm ': time to the onset demand after opening, slowest case'], (tl(end) - p.in_t_open)*1e3, NaN, 'ms');
            ka_report('add', ['N1.at.' o],    [nm ': at the onset, slowest case (N1-1 >= 90 %)'], min([M0.onset_pct]), NaN, '%');
            ka_report('add', ['N1.bef.' o],   [nm ': torque x time before the onset (N1-2 <= 10 %)'], max([M0.before_pct]), NaN, '%');
            ka_report('add', ['N1.mis.' o],   [nm ': torque x time missing in the window (N1-3 <= 10 %)'], max([M0.missing_pct]), NaN, '%');
            ka_report('add', ['N1.over.' o],  [nm ': torque x time above the asked curve (information)'], max([M0.over_pct]), NaN, '%');
            ka_report('add', ['N1.pkl.' o],   [nm ': peak, lowest case'], min([M0.peak_pct]), NaN, '% target');
            ka_report('add', ['N1.pkh.' o],   [nm ': peak, highest case'], max([M0.peak_pct]), NaN, '% target');
            ka_report('add', ['N1.imp.' o],   [nm ': device torque x time in the window, slowest case'], M0(1).impulse_Nms, NaN, 'N m s');
            ka_report('add', ['N1.ask.' o],   [nm ': torque x time asked in the window'], M0(1).asked_Nms, NaN, 'N m s');
            br = [M.back_rest_ms];
            ka_report('add', ['N4.bl.' o],    [nm ': back at 2.4 kPa(g), earliest'], min(br), NaN, 'ms');
            ka_report('add', ['N4.bh.' o],    [nm ': back at 2.4 kPa(g), latest'], max(br), NaN, 'ms');
            ka_report('add', ['N4.marg.' o],  [nm ': margin to the 613 ms deadline (N4-1)'], p.t_deadline*1e3 - max(br), NaN, 'ms');
            ka_report('add', ['N4.pdl.' o],   [nm ': pressure at 613 ms'], max([M.p_deadline_kPa]), NaN, 'kPa');
            ka_report('add', ['N4.ps.' o],    [nm ': highest pressure while knee <= 0 deg, clock -4 ms (N4-4 <= 2.4)'], max([Me.p_straight_kPa]), NaN, 'kPa');
            ka_report('add', ['N4.fa.' o],    [nm ': first above 2.4 kPa(g), clock -4 ms'], min([Me.first_above_ms]), NaN, 'ms');
            ka_report('add', ['N1.rate.' o],  [nm ': fill rate at half the set point, slowest case'], ...
                      p.R * p.T0 / p.V * ka_lookup_in(p, 53, p.cap_kPa / 2) / 1e3, NaN, 'kPa/s');
            R.p{nin, pc, w} = p;  R.M{nin, pc, w} = M;  R.scan{nin, pc, w} = scan;
        end
    end
end
ka_report('add', 'N1.knee0', 'Knee passes 0 deg (B4)', R.M{1,1,2}(2,1).t_knee0_ms, 42, 'ms');

%% ---- figures ----
if make_figs
    C = ka_colours();
    for w = [2 1]
        figure('Name', sprintf('Demand pulses window %d', w), 'Color', 'w', 'Position', [60 60 1150 440]);
        for pc = 1:2
            subplot(1, 2, pc);  hold on;  grid on;
            p = R.p{1, pc, w};
            tg = (0:0.25:400) / 1e3;
            dem = min(ka_torque_req(p, tg) / p.k_Nm_per_kPa, p.cap_kPa);  dem(dem <= 0) = NaN;
            plot(tg*1e3, dem, '--', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.4, 'DisplayName', 'asked: \tau_{req} / k');
            % one MHJ10, fastest case (adiabatic, 70 kPa receiver); two MHE3 at the port
            col = {C.s2};  sty = {'-'};  nex = 2;
            for k = 1:numel(nex)
                rf = ka_simulate(p, ka_default_cfg('pulse','demand','n_exh',nex(k),'exh_at_port',true,'t_end',0.66, ...
                                                   'adiabatic', true, 'pr_kPa', 70));
                plot(rf.log.t*1e3, rf.log.p, sty{k}, 'Color', col{k}, 'LineWidth', 1.8, ...
                     'DisplayName', sprintf('%d MHE3 at the port', nex(k)));
            end
            xline(p.t_on*1e3, '-', 'onset', 'Color', [0.6 0.6 0.6], 'HandleVisibility', 'off');
            xline(p.t_off*1e3, '-', 'offset', 'Color', [0.6 0.6 0.6], 'HandleVisibility', 'off');
            xlim([30 380]);  ylim([0 30]);  xlabel('time after contact (ms)');  ylabel('bladder (kPa(g))');
            title({sprintf('%s, %s: \\alpha %.3f', p.win_name, p.opt_name, p.alpha), 'one MHJ10, fastest case'});
            if pc == 1, legend('Location', 'north'); end   % 20 kPa panel: free space above the pulse
        end
        ka_savefig(sprintf('fig%02d_demand_pulses_w%d', 10 - w, w));
    end

    figure('Name', 'Knee angle and pressure', 'Color', 'w', 'Position', [60 60 1150 620]);
    p = R.p{1, 1, 2};
    r0 = ka_simulate(p, ka_default_cfg('adiabatic', true, 'pr_kPa', 70, spec{:}, 't_end', p.T_stride));
    re = ka_simulate(p, ka_default_cfg('adiabatic', true, 'pr_kPa', 70, 'clock_err', -0.004, spec{:}));
    lims = {[0 p.T_stride*1e3], [0 140]};  runs = {r0, re};
    ttl = {'Whole stride: window 2, 20 kPa, one MHJ10, clock right', 'First 140 ms: clock 4 ms early (fastest case)'};
    for j = 1:2
        subplot(2, 2, j);  hold on;  grid on;
        plot(p.b4_t*1e3, p.b4_deg, 'Color', C.s3, 'LineWidth', 2);
        yline(0, ':', 'straight', 'Color', C.ink);
        if j == 1
            xline(p.t_deadline*1e3, '--', '613 ms', 'Color', C.ink);  xline(p.T_stance*1e3, ':', 'toe-off', 'Color', C.ink);
        else
            xline(42, ':', 'knee 0 deg', 'Color', C.ink);  xline(p.t_on*1e3, '-', 'onset 91.65 ms', 'Color', C.ink);
        end
        xlim(lims{j});  ylabel('knee flexion (deg)');  title(ttl{j});
        subplot(2, 2, j + 2);  hold on;  grid on;
        plot(runs{j}.log.t*1e3, runs{j}.log.p, 'Color', C.s2, 'LineWidth', 2);
        yline(p.rest_kPa, ':', '2.4 kPa', 'Color', C.ink);
        xlim(lims{j});  xlabel('time after contact (ms)');  ylabel('bladder (kPa(g))');
    end
    ka_savefig('fig10_knee_angle_pressure');

    figure('Name', 'Device torque', 'Color', 'w', 'Position', [60 60 1150 440]);
    for pc = 1:2
        subplot(1, 2, pc);  hold on;  grid on;
        tg = (0:0.25:400) / 1e3;
        pm = R.p{1, pc, 2};
        plot(pm.pm_pct/100*705, pm.pm_Nm, 's-', 'Color', C.s3, 'MarkerSize', 3, 'DisplayName', 'patient''s own moment');
        sty = {'-', '--'};
        for w = [2 1]
            p = R.p{1, pc, w};
            tq = min(ka_torque_req(p, tg), p.k_Nm_per_kPa * p.cap_kPa);  tq(tq <= 0) = NaN;
            plot(tg*1e3, tq, sty{3-w}, 'Color', [0.45 0.45 0.45], 'LineWidth', 1.3, 'DisplayName', sprintf('asked, %s', p.win_name));
            rs = ka_simulate(p, ka_default_cfg('adiabatic', false, 'pr_kPa', 53, spec{:}));
            plot(rs.log.t*1e3, p.k_Nm_per_kPa * max(rs.log.p, 0), sty{3-w}, 'Color', ifelse(w == 2, C.s2, C.s1), 'LineWidth', 1.8, ...
                 'DisplayName', sprintf('delivered k x p, %s (slowest case)', p.win_name));
        end
        xlim([40 380]);  ylim([0 9]);  xlabel('time after contact (ms)');  ylabel('moment (N m)');
        title(sprintf('%s, one MHJ10, two MHE3', R.p{1, pc, 2}.opt_name));
        if pc == 1, legend('Location', 'northeast'); end
    end
    ka_savefig('fig11_device_torque');
end
fprintf('N1 / N4 done in %.1f min\n', toc(t0) / 60);
end
function v = ifelse(c, a, b), if c, v = a; else, v = b; end, end

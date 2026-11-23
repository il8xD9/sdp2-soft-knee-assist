function R = run27_inputs(make_figs)
%RUN27_INPUTS  Rev 27 inputs: Basem's curves, the torque relation, alpha, onset
%   demands, exhaust capacity and the swing squeeze (no time simulation).
%   Figures 1 (Basem inputs), 2 (torque - pressure), 3 (swing squeeze).
if nargin < 1, make_figs = true; end
fprintf('\n===== Rev 27 inputs: Basem curves, torque relation, swing squeeze =====\n');
base = ka_setup(1, 1, 2, 'timing', false);
R.base = base;
C = ka_colours();

%% ---- torque relation, alpha, required pressure ----
k3 = base.k3D * 1e3;  k2 = base.A_i * (base.d_h + base.d_off) * 1e3;
ka_report('add', 'k.3D', 'Torque per kPa, 3D virtual work (k3D = 206 990 mm^3)', k3, 0.20699, 'N m/kPa');
ka_report('add', 'k.2D', 'Torque per kPa, flat section A_i (d_h + 28 mm)', k2, 0.19871, 'N m/kPa');
for pc = 1:2
    for w = [2 1]
        p = ka_case(base, pc, w);  o = sprintf('%s.%s', p.opt_short, p.win_short);
        ka_report('add', ['alpha.' o], sprintf('%s, %s: design alpha', p.opt_name, p.win_name), p.alpha, pick(pc, 0.1255, 0.1694), '-');
        ka_report('add', ['Mz.' o], sprintf('%s, %s: torque at the set point', p.opt_name, p.win_name), p.k_Nm_per_kPa * p.cap_kPa, pick(pc, 4.140, 5.589), 'N m');
        ka_report('add', ['pon.' o], sprintf('%s, %s: onset demand', p.opt_name, p.win_name), p.p_on_kPa, ifelse(w == 2, 6.88, pick(pc, 4.28, 5.77)), 'kPa');
        ka_report('add', ['tqon.' o], sprintf('%s, %s: torque asked at the onset', p.opt_name, p.win_name), p.tq_on, ifelse(w == 2, 1.424, pick(pc, 0.885, 1.195)), 'N m');
        ka_report('add', ['tqoff.' o], sprintf('%s, %s: torque asked at the offset', p.opt_name, p.win_name), p.tq_off, ifelse(w == 2, 0.583, pick(pc, 0.777, 1.050)), 'N m');
        tg = (p.t_on : 1e-4 : p.t_off);
        dem = min(ka_torque_req(p, tg) / p.k_Nm_per_kPa, p.cap_kPa);
        ka_report('add', ['rise.' o], sprintf('%s, %s: steepest pressure rise asked', p.opt_name, p.win_name), max(diff(dem)) / 1e-4, NaN, 'kPa/s');
        ka_report('add', ['fall.' o], sprintf('%s, %s: steepest pressure fall asked', p.opt_name, p.win_name), -min(diff(dem)) / 1e-4, NaN, 'kPa/s');
        imp = trapz(tg, ka_torque_req(p, tg));
        ka_report('add', ['imp.' o], sprintf('%s, %s: torque x time asked per stride', p.opt_name, p.win_name), imp, NaN, 'N m s');
        R.case{pc, w} = p;
    end
end
ka_report('add', 'p.6.6',  'Pressure needed for the test value 6.6 N m (alpha 0.20)', 6.6 / k3, 31.9, 'kPa');
ka_report('add', 'p.8.39', 'Pressure needed for the requirement 8.39 N m (alpha 0.254)', 0.254 * 32.9675 / k3, 40.5, 'kPa');
ka_report('add', 'V.sys', 'Air volume: cavity 390.93 + tube', base.V * 1e6, 391.9, 'mL');
ka_report('add', 't.on.W1', 'Window 1 onset', 8.43/100*705, 59.4, 'ms');
ka_report('add', 't.on.W2', 'Window 2 onset', 13/100*705, 91.65, 'ms');
ka_report('add', 'vent.W1', 'Time to vent, window 1 offset to 613 ms', (0.87 - 0.44) * 705, 303.2, 'ms');
ka_report('add', 'vent.W2', 'Time to vent, window 2 offset to 613 ms', (0.87 - 0.36) * 705, 359.6, 'ms');

%% ---- exhaust capacity at 2.4 kPa and swing squeeze ----
rho24 = (base.rest_kPa * 1e3 + base.p_atm) / (base.R * base.T0);
Qsw3 = base.swing_dVdeg * base.knee_rate / 1e3;     % l/s, 3D
Qsw2 = 4.03 * base.knee_rate / 1e3;                 % l/s, Rev 25 flat estimate
ka_report('add', 'swing.dVdeg', 'Swing squeeze, 3D: k3D x pi/180', base.k3D * 1e9 * pi / 180 / 1e3, 3.613, 'mL/deg');
ka_report('add', 'swing.Q', 'Swing squeeze flow at 261 deg/s (3D)', Qsw3, 0.943, 'l/s');
ka_report('add', 'swing.V', 'Air pushed out over 27.8 -> 65 deg (3D)', base.swing_dVdeg * (65 - 27.81), 134.4, 'mL');
ka_report('add', 'swing.Mres', 'Trapped-air moment at 2.4 kPa (3D)', 2.4 * k3, 0.497, 'N m');
hand_port = [0.2185 0.437 0.6555 0.874 1.0925 1.311];
for n = 1:base.ex_nmax
    ct = ka_lookup_ex(base, ka_excol(base, n, false), base.rest_kPa) / rho24 * 1e3;
    cp = ka_lookup_ex(base, ka_excol(base, n, true),  base.rest_kPa) / rho24 * 1e3;
    R.cap_tube(n) = ct;  R.cap_port(n) = cp;
    ka_report('add', sprintf('cap.tube.n%d', n), sprintf('%d MHE3 through the tube: capacity at 2.4 kPa', n), ct, NaN, 'l/s');
    ka_report('add', sprintf('cap.port.n%d', n), sprintf('%d MHE3 at the port: capacity at 2.4 kPa', n), cp, hand_port(n), 'l/s');
    ka_report('add', sprintf('allow.port.n%d', n), sprintf('%d MHE3 at the port: volume loss allowed at 261 deg/s', n), cp * 1e3 / base.knee_rate, NaN, 'mL/deg');
    if n >= 2
        R.peq3(n) = swing_peq(base, Qsw3, n);  R.peq2(n) = swing_peq(base, Qsw2, n);
        ka_report('add', sprintf('peq.3D.n%d', n), sprintf('Bag pushing %.3f l/s through %d MHE3 at the port: pressure', Qsw3, n), R.peq3(n), NaN, 'kPa');
        ka_report('add', sprintf('peq.2D.n%d', n), sprintf('Bag pushing %.3f l/s (Rev 25 flat) through %d MHE3: pressure', Qsw2, n), R.peq2(n), NaN, 'kPa');
    end
end
ka_report('add', 'n.exh.needed', 'MHE3 needed at the port for the 3D swing squeeze (<= 2.4 kPa)', find(R.cap_port >= Qsw3, 1), 5, '-');
R.Qsw3 = Qsw3;  R.Qsw2 = Qsw2;

%% ---- figures ----
if make_figs
    % Figure 1: Basem's inputs
    p2 = R.case{1, 2};  p1 = R.case{1, 1};  p27 = R.case{2, 2};  p17 = R.case{2, 1};
    figure('Name', 'Basem inputs', 'Color', 'w', 'Position', [60 60 1150 820]);
    tg = (0:0.25:400) / 1e3;
    subplot(3, 1, 1);  hold on;  grid on;
    s = p1.b3_pct;  plot(s / 100 * 705, p1.b3_def, 'Color', C.ink, 'LineWidth', 1.8, 'DisplayName', '\tau_{full}: full deficit (\alpha = 1), pchip through Basem''s points');
    plot(p1.b3_pts(:,1) / 100 * 705, p1.b3_pts(:,2), 'o', 'Color', C.ink, 'MarkerSize', 4, 'HandleVisibility', 'off');
    plot(p1.pm_pct / 100 * 705, p1.pm_Nm, 's-', 'Color', C.s3, 'LineWidth', 1.6, 'MarkerSize', 4, 'DisplayName', 'patient''s own moment (window 2 cap)');
    patch([59.4 310.2 310.2 59.4], [0 0 36 36], C.s1, 'FaceAlpha', 0.06, 'EdgeColor', 'none', 'DisplayName', 'window 1, 8.43-44 %');
    patch([91.65 253.8 253.8 91.65], [0 0 36 36], C.s2, 'FaceAlpha', 0.10, 'EdgeColor', 'none', 'DisplayName', 'window 2, 13-36 % (main)');
    xlim([0 400]);  ylim([0 36]);  ylabel('moment (N m)');  legend('Location', 'northeast');
    title('Basem O1 v10 / O2 v3: deficit and patient moment (2 months after ACLR, 70 kg, 1.70 m, 1.17 m/s)');
    subplot(3, 1, 2);  hold on;  grid on;
    cases = {p2, p27, p1, p17};  st = {'-', '-', '--', '--'};  cl = {C.s1, C.s2, C.s1, C.s2};
    for j = 1:4
        q = cases{j};  tq = min(ka_torque_req(q, tg), q.k_Nm_per_kPa * q.cap_kPa);  tq(tq <= 0) = NaN;
        plot(tg * 1e3, tq, st{j}, 'Color', cl{j}, 'LineWidth', 1.7, 'DisplayName', sprintf('%s, %s: \\alpha %.3f', q.win_name, q.opt_name, q.alpha));
    end
    tq = 0.20 * ka_deficit(p1, tg);  tq(tq <= 0) = NaN;
    plot(tg * 1e3, tq, ':', 'Color', C.ink, 'LineWidth', 1.3, 'DisplayName', 'test value \alpha 0.20 (window 1, not reachable)');
    xlim([0 400]);  ylabel('torque asked (N m)');  legend('Location', 'northeast');
    title('Torque asked at the design \alpha (3D k = 0.207 N m/kPa): window 2 capped at the patient''s moment');
    subplot(3, 1, 3);  hold on;  grid on;
    plot(p1.b4_t * 1e3, p1.b4_deg, 'Color', C.s3, 'LineWidth', 1.8);
    plot(p1.b4_pts(:,1) / 100 * 705, p1.b4_pts(:,2), 'o', 'Color', C.s3, 'MarkerSize', 4);
    yline(0, ':', 'straight', 'Color', C.ink);  xline(42, ':', '0 deg at 42 ms', 'Color', C.ink);
    xline(613.35, '--', '613 ms: 10.4 deg', 'Color', C.ink);  xline(705, ':', 'toe-off 27.8 deg', 'Color', C.ink);
    xlim([0 1175]);  xlabel('time after initial contact (ms)');  ylabel('knee flexion (deg)');
    title('Basem B4 knee angle (O1 v10) with the healthy swing peak 65 deg');
    ka_savefig('fig01_basem_inputs');

    % Figure 2: torque - pressure
    figure('Name', 'Torque relation', 'Color', 'w', 'Position', [60 60 1150 430]);
    subplot(1, 2, 1);  hold on;  grid on;
    pp = 0:0.5:45;
    plot(pp, k3 * pp, 'Color', C.s1, 'LineWidth', 2, 'DisplayName', sprintf('3D virtual work: k = %.4f N m/kPa (used)', k3));
    plot(pp, k2 * pp, '--', 'Color', C.ink, 'LineWidth', 1.4, 'DisplayName', sprintf('flat section: k = %.4f N m/kPa', k2));
    xline(20, '-', '20 kPa design', 'Color', C.s1, 'HandleVisibility', 'off');
    xline(27, '-', '27 kPa side case', 'Color', C.s2, 'HandleVisibility', 'off');
    xline(28.9, ':r', 'pain onset 28.9', 'HandleVisibility', 'off');
    yline(6.6, ':', 'test 6.6 N m (31.9 kPa)', 'HandleVisibility', 'off');
    yline(8.39, ':', 'requirement 8.39 N m (40.5 kPa)', 'HandleVisibility', 'off');
    plot([20 27], k3 * [20 27], 'o', 'Color', C.s1, 'MarkerFaceColor', C.s1, 'HandleVisibility', 'off');
    text(20.5, k3 * 20 - 0.45, sprintf('%.2f N m', k3 * 20));  text(27.5, k3 * 27 - 0.45, sprintf('%.2f N m', k3 * 27));
    xlabel('bladder pressure (kPa(g))');  ylabel('device moment (N m)');  legend('Location', 'northwest');
    title('Moment = k x pressure (d_h 65 mm)');
    subplot(1, 2, 2);  hold on;  grid on;
    dh = 0:1:80;  kk = interp1(base.k3D_band(1,:), base.k3D_band(2,:), dh) * 1e-6;
    plot(dh, 20 * kk / 33, 'Color', C.s1, 'LineWidth', 2, 'DisplayName', '\alpha at 20 kPa (3D)');
    plot(dh, 27 * kk / 33, 'Color', C.s2, 'LineWidth', 2, 'DisplayName', '\alpha at 27 kPa (3D)');
    plot(dh, 20 * base.A_i * (dh/1e3 + 0.028) * 1e3 / 33, '--', 'Color', C.s1, 'DisplayName', '\alpha at 20 kPa (flat section)');
    yline(0.20, ':', 'test value 0.20', 'HandleVisibility', 'off');  yline(0.254, ':', 'requirement 0.254', 'HandleVisibility', 'off');
    xline(65, '-', 'd_h 65 mm (record)', 'Color', C.ink, 'HandleVisibility', 'off');
    xlabel('hinge depth d_h (mm)');  ylabel('design \alpha');  ylim([0 0.3]);  legend('Location', 'northwest');
    title('Design \alpha over the hinge band (no source for d_h)');
    ka_savefig('fig02_torque_pressure');

    % Figure 3: swing squeeze
    figure('Name', 'Swing squeeze', 'Color', 'w', 'Position', [60 60 1150 400]);
    subplot(1, 2, 1);  hold on;  grid on;
    bar(1:6, R.cap_port, 0.6, 'FaceColor', C.s1, 'EdgeColor', 'none', 'DisplayName', 'n MHE3 at the port, at 2.4 kPa');
    yline(Qsw3, '-', sprintf('3D squeeze %.2f l/s', Qsw3), 'Color', C.s2, 'LineWidth', 1.6, 'HandleVisibility', 'off');
    yline(Qsw2, '--', sprintf('Rev 25 flat estimate %.2f l/s', Qsw2), 'Color', C.ink, 'HandleVisibility', 'off');
    xlabel('number of MHE3 exhausts at the bladder port');  ylabel('flow at the 2.4 kPa rest level (l/s)');
    title('Exhaust capacity against the swing squeeze');
    subplot(1, 2, 2);  hold on;  grid on;
    plot(2:6, R.peq3(2:6), 'o-', 'Color', C.s2, 'LineWidth', 1.8, 'DisplayName', sprintf('3D: %.3f l/s (Rev 27)', Qsw3));
    plot(2:6, R.peq2(2:6), 's--', 'Color', C.ink, 'LineWidth', 1.4, 'DisplayName', sprintf('flat: %.3f l/s (Rev 25)', Qsw2));
    yline(2.4, ':r', '2.4 kPa rest limit', 'HandleVisibility', 'off');
    set(gca, 'YScale', 'log');  xlabel('number of MHE3 at the port');  ylabel('bladder pressure in swing (kPa(g))');
    legend('Location', 'northeast');  title('Pressure the swing squeeze builds (equilibrium bound)');
    ka_savefig('fig03_swing_squeeze');
end
end

%% =====================================================================
function pk = swing_peq(p, Q_ls, n)
lo = 0.01;  hi = 40;
for it = 1:60
    mid = 0.5 * (lo + hi);  P = mid * 1e3 + p.p_atm;  rho = P / (p.R * p.T0);
    q = ka_series_flow('exhaust', P, p.p_atm, n, 1, p) / rho * 1e3;
    if q > Q_ls, hi = mid; else, lo = mid; end
end
pk = 0.5 * (lo + hi);
end
function v = pick(i, a, b), if i == 1, v = a; else, v = b; end, end
function v = ifelse(c, a, b), if c, v = a; else, v = b; end, end

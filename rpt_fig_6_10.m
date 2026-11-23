function V = rpt_fig_6_10(p)
%RPT_FIG_6_10  Report Figure 6.10: swing squeeze with two exhaust valves at the bladder port.
%   Left:  flow of the pair at the 2.4 kPa(g) rest level (l/s at the bladder) for
%          2 x MHE3 (200 Nl/min), 2 x MHE4 (400 Nl/min), 2 x 440 Nl/min (minimum),
%          2 x 630 Nl/min (recommended), against the 3D squeeze 0.943 l/s and the
%          flat-section estimate 1.05 l/s (Table M.11).
%   Right: pressure the squeeze builds in the vented bladder (equilibrium bound) against
%          the standard nominal flow of each of the two exhausts, b = 0.36 (band b = 0..0.53).
%   Each exhaust: C from its nominal flow (ka_exhaust_from_qn), ISO 6358 flow at the port
%   (ka_series_flow, at_port = 1). Squeeze Q = k3D x pi/180 x 261 deg/s.
if nargin < 1 || isempty(p), p = rpt_base(); end
C = ka_colours();
b0 = 0.36;
Q3 = p.swing_dVdeg * p.knee_rate / 1e3;          % l/s, 3D squeeze (0.943)
Q2 = 4.03 * p.knee_rate / 1e3;                   % l/s, flat-section estimate (1.05)
P24 = p.rest_kPa * 1e3 + p.p_atm;
rho24 = P24 / (p.R * p.T0);

qn_bar = [200 400 440 630];
names  = {'2 x MHE3\newline200 Nl/min each', '2 x MHE4\newline400 Nl/min each', ...
          '2 x 440 Nl/min\newline(minimum)', '2 x 630 Nl/min\newline(recommended)'};
Qpair = zeros(size(qn_bar));
for i = 1:numel(qn_bar)
    q = ka_exhaust_from_qn(p, qn_bar(i), b0);
    Qpair(i) = ka_series_flow('exhaust', P24, p.p_atm, 2, 1, q) / rho24 * 1e3;
end

qn = 150:5:750;
pe3 = zeros(size(qn));  pe2 = pe3;  peLo = pe3;  peHi = pe3;
for i = 1:numel(qn)
    pe3(i)  = swing_peq(ka_exhaust_from_qn(p, qn(i), b0),   Q3);
    pe2(i)  = swing_peq(ka_exhaust_from_qn(p, qn(i), b0),   Q2);
    peLo(i) = swing_peq(ka_exhaust_from_qn(p, qn(i), 0.53), Q3);
    peHi(i) = swing_peq(ka_exhaust_from_qn(p, qn(i), 0),    Q3);
end
peBar = zeros(size(qn_bar));
for i = 1:numel(qn_bar)
    peBar(i) = swing_peq(ka_exhaust_from_qn(p, qn_bar(i), b0), Q3);
end

figure('Name', 'Report Figure 6.10', 'Color', 'w', 'Position', [60 60 1150 440]);
tl = tiledlayout(1, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

ax1 = nexttile(tl);  hold(ax1, 'on');  grid(ax1, 'on');  box(ax1, 'on');
bc = [0.33 0.33 0.33; 0.62 0.73 0.87; C.s1; C.s1];
hb = bar(ax1, 1:4, Qpair, 0.62, 'FaceColor', 'flat', 'EdgeColor', 'none');
hb.CData = bc;
for i = 1:4
    tc = 'w';  if i == 2, tc = 'k'; end
    text(ax1, i, Qpair(i) * 0.5, sprintf('%.3f l/s', Qpair(i)), 'HorizontalAlignment', 'center', ...
         'FontWeight', 'bold', 'FontSize', 8, 'Color', tc);
end
yline(ax1, Q3, '-', sprintf('3D squeeze %.3f l/s', Q3), 'Color', C.s2, 'LineWidth', 1.6, ...
      'LabelHorizontalAlignment', 'left');
yline(ax1, Q2, '--', sprintf('flat-section estimate %.2f l/s', Q2), 'Color', C.ink, ...
      'LabelHorizontalAlignment', 'left');
set(ax1, 'XTick', 1:4, 'XTickLabel', names, 'TickLabelInterpreter', 'tex');
xlim(ax1, [0.4 4.6]);  ylim(ax1, [0 1.6]);
ylabel(ax1, 'flow of the pair at the 2.4 kPa rest level (l/s)');
title(ax1, 'Two exhausts at the bladder port: capacity against the squeeze');

ax2 = nexttile(tl);  hold(ax2, 'on');  grid(ax2, 'on');  box(ax2, 'on');
hf = fill(ax2, [qn fliplr(qn)], [peLo fliplr(peHi)], C.s2, 'FaceAlpha', 0.15, 'EdgeColor', 'none');
h3 = plot(ax2, qn, pe3, '-', 'Color', C.s2, 'LineWidth', 1.8);
h2 = plot(ax2, qn, pe2, '--', 'Color', C.ink, 'LineWidth', 1.4);
yline(ax2, p.rest_kPa, ':', sprintf('N4-2 limit %.1f kPa', p.rest_kPa), 'Color', 'r', ...
      'LabelHorizontalAlignment', 'right', 'HandleVisibility', 'off');
xm = [200 400 440 630];  xl = {'MHE3', 'MHE4', '440 Nl/min', '630 Nl/min'};
for i = 1:4
    xline(ax2, xm(i), ':', xl{i}, 'Color', [0.55 0.55 0.55], 'LabelVerticalAlignment', 'bottom', ...
          'FontSize', 7, 'HandleVisibility', 'off');
end
set(ax2, 'YScale', 'log');
xlim(ax2, [150 750]);  ylim(ax2, [0.8 50]);
xlabel(ax2, 'standard nominal flow of each of the two exhausts (Nl/min)');
ylabel(ax2, 'bladder pressure in swing (kPa(g))');
legend(ax2, [h3 h2 hf], {sprintf('3D squeeze %.3f l/s', Q3), sprintf('flat estimate %.2f l/s', Q2), ...
       '3D, b = 0 to 0.53'}, 'Location', 'northeast');
title(ax2, 'Pressure the swing squeeze builds (equilibrium bound)');

V.Q3 = Q3;  V.Q2 = Q2;  V.qn = qn_bar;  V.Qpair = Qpair;  V.p_eq = peBar;
V.M_trapped = peBar * p.k_Nm_per_kPa;
fprintf('Figure 6.10: squeeze %.3f l/s (3D), %.3f l/s (flat)\n', Q3, Q2);
fprintf('             pair flow at 2.4 kPa = %.3f / %.3f / %.3f / %.3f l/s (MHE3 / MHE4 / 440 / 630; report 0.438 / 0.875 / 0.963 / 1.379)\n', Qpair);
fprintf('             swing pressure       = %.2f / %.2f / %.2f / %.2f kPa (report 13.3 / 2.7-2.9 / 2.3 / 1.1)\n', peBar);
fprintf('             trapped-air moment   = %.2f / %.2f / %.2f / %.2f N m (report 2.75 / - / 0.48 / 0.23)\n', V.M_trapped);
end

function pk = swing_peq(q, Q_ls)
% bladder pressure (kPa(g)) at which two exhausts at the port pass Q_ls (l/s at the bladder)
lo = 0.001;  hi = 200;
for it = 1:70
    mid = 0.5 * (lo + hi);  P = mid * 1e3 + q.p_atm;  rho = P / (q.R * q.T0);
    Q = ka_series_flow('exhaust', P, q.p_atm, 2, 1, q) / rho * 1e3;
    if Q > Q_ls, hi = mid; else, lo = mid; end
end
pk = 0.5 * (lo + hi);
end

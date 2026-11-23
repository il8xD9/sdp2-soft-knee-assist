function V = rpt_fig_M4(p)
%RPT_FIG_M4  Report Figure M.4: torque relation, re-plotted from the closed-form
%   relations of Appendix J (HC-10 to HC-12).
%   Left:  moment = k x pressure at d_h 65 mm, 3D constant (used) and flat section,
%          with the test value 6.6 N m (31.9 kPa) and the upper bound alpha_max = 0.25
%          (8.25 N m at 39.9 kPa).
%   Right: design alpha over the hinge band (no source for d_h).
%   Same content as results\fig02 of run27_inputs, with the report's labels.
if nargin < 1 || isempty(p), p = rpt_base(); end
C = ka_colours();
k3 = p.k3D * 1e3;
k2 = p.A_i * (p.d_h + p.d_off) * 1e3;

figure('Name', 'Report Figure M.4', 'Color', 'w', 'Position', [60 60 1150 430]);
tl = tiledlayout(1, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

ax1 = nexttile(tl);  hold(ax1, 'on');  grid(ax1, 'on');  box(ax1, 'on');
pp = 0:0.5:45;
plot(ax1, pp, k3 * pp, 'Color', C.s1, 'LineWidth', 2, 'DisplayName', sprintf('3D virtual work: k = %.4f N m/kPa (used)', k3));
plot(ax1, pp, k2 * pp, '--', 'Color', C.ink, 'LineWidth', 1.4, 'DisplayName', sprintf('flat section: k = %.4f N m/kPa', k2));
xline(ax1, 20, '-', '20 kPa design', 'Color', C.s1, 'HandleVisibility', 'off');
xline(ax1, 27, '-', '27 kPa side case', 'Color', C.s2, 'HandleVisibility', 'off');
xline(ax1, p.pain_kPa, ':r', sprintf('pain onset %.1f', p.pain_kPa), 'HandleVisibility', 'off');
yline(ax1, 6.6, ':', sprintf('test value 6.6 N m (%.1f kPa)', 6.6 / k3), 'HandleVisibility', 'off');
yline(ax1, 8.25, ':', sprintf('upper bound \\alpha_{max} = 0.25 (8.25 N m at %.1f kPa)', 8.25 / k3), 'HandleVisibility', 'off');
plot(ax1, [20 27], k3 * [20 27], 'o', 'Color', C.s1, 'MarkerFaceColor', C.s1, 'HandleVisibility', 'off');
text(ax1, 20.5, k3 * 20 - 0.45, sprintf('%.2f N m', k3 * 20));
text(ax1, 27.5, k3 * 27 - 0.45, sprintf('%.2f N m', k3 * 27));
xlabel(ax1, 'bladder pressure (kPa(g))');  ylabel(ax1, 'device moment (N m)');
legend(ax1, 'Location', 'southeast');  ylim(ax1, [0 10]);
title(ax1, 'Moment = k x pressure (d_h = 65 mm)');

ax2 = nexttile(tl);  hold(ax2, 'on');  grid(ax2, 'on');  box(ax2, 'on');
dh = 0:1:80;
kk = interp1(p.k3D_band(1, :), p.k3D_band(2, :), dh) * 1e-6;
plot(ax2, dh, 20 * kk / p.def_peak, 'Color', C.s1, 'LineWidth', 2, 'DisplayName', '\alpha at 20 kPa (3D)');
plot(ax2, dh, 27 * kk / p.def_peak, 'Color', C.s2, 'LineWidth', 2, 'DisplayName', '\alpha at 27 kPa (3D)');
plot(ax2, dh, 20 * p.A_i * (dh / 1e3 + p.d_off) * 1e3 / p.def_peak, '--', 'Color', C.s1, 'DisplayName', '\alpha at 20 kPa (flat section)');
yline(ax2, 0.20, ':', 'test value 0.20', 'HandleVisibility', 'off');
yline(ax2, 0.25, ':', 'upper bound 0.25', 'HandleVisibility', 'off');
xline(ax2, 65, '-', 'd_h 65 mm (design of record)', 'Color', C.ink, 'HandleVisibility', 'off');
xlabel(ax2, 'hinge depth d_h (mm)');  ylabel(ax2, 'design \alpha');  ylim(ax2, [0 0.3]);
legend(ax2, 'Location', 'northwest');
title(ax2, 'Design \alpha over the hinge band (no source for d_h)');

V.k3 = k3;  V.k2 = k2;  V.p66 = 6.6 / k3;  V.p825 = 8.25 / k3;
fprintf('Figure M.4: k = %.4f (3D) / %.4f (flat) N m/kPa; 6.6 N m at %.1f kPa, 8.25 N m at %.1f kPa\n', k3, k2, V.p66, V.p825);
end

function V = rpt_fig_M3(p)
%RPT_FIG_M3  Report Figure M.3: pressure needed at the peak against alpha over the
%   hinge-depth band, with the 20 kPa design point, the 27 kPa calibrated limit and the
%   reference level 28.9 kPa (pain onset).
%   p_req = alpha x tau_full / k3D(d_h), tau_full = 33.00 N m (Eq. 4.12); d_h 50 / 65 / 80 mm.
if nargin < 1 || isempty(p), p = rpt_base(); end
al = 0:0.005:0.30;
dh = [50 65 80];
kk = interp1(p.k3D_band(1, :), p.k3D_band(2, :), dh) * 1e-6;   % N m / kPa
col = {[0.45 0.66 0.90], [0.09 0.27 0.58], [0.20 0.48 0.82]};
lw  = [1.2 3.0 1.2];

figure('Name', 'Report Figure M.3', 'Color', 'w', 'Position', [60 60 900 480]);
hold on;  grid on;  box on;
h = gobjects(1, 3);  lab = cell(1, 3);
for i = 1:3
    h(i) = plot(al, al * p.def_peak / kk(i), '-', 'Color', col{i}, 'LineWidth', lw(i));
    lab{i} = sprintf('d_h = %d mm', dh(i));
end
lab{2} = 'd_h = 65 mm (design basis)';
yline(p.pain_kPa, '--', sprintf('pain onset %.1f kPa', p.pain_kPa), 'Color', [0.35 0.35 0.35], ...
      'LabelHorizontalAlignment', 'left', 'HandleVisibility', 'off');
yline(27, '--', '27 kPa calibrated limit', 'Color', [0.5 0.5 0.5], 'LabelHorizontalAlignment', 'left', ...
      'LabelVerticalAlignment', 'bottom', 'HandleVisibility', 'off');
yline(20, ':', '20 kPa design point', 'Color', [0.5 0.5 0.5], 'LabelHorizontalAlignment', 'left', ...
      'HandleVisibility', 'off');
xline(0.20, ':', 'test value \alpha = 0.20', 'Color', [0.3 0.3 0.3], 'LabelVerticalAlignment', 'bottom', 'HandleVisibility', 'off');
xline(0.25, ':', 'requirement \alpha = 0.25', 'Color', [0.3 0.3 0.3], 'LabelVerticalAlignment', 'bottom', 'HandleVisibility', 'off');
pa = [0.20 0.25] * p.def_peak / kk(2);
plot([0.20 0.25], pa, 'ko', 'MarkerFaceColor', 'k', 'MarkerSize', 6, 'HandleVisibility', 'off');
text(0.185, pa(1) + 4, sprintf('%.1f kPa', pa(1)), 'HorizontalAlignment', 'right');
text(0.235, pa(2) + 6, sprintf('%.1f kPa', pa(2)), 'HorizontalAlignment', 'right');
plot([0.187 0.20], [pa(1) + 3.6 pa(1)], '-', 'Color', [0.3 0.3 0.3], 'HandleVisibility', 'off');
plot([0.237 0.25], [pa(2) + 5.6 pa(2)], '-', 'Color', [0.3 0.3 0.3], 'HandleVisibility', 'off');
xlim([0 0.30]);  ylim([0 60]);
xlabel('Assistance ratio \alpha');  ylabel('Pressure needed at the peak (kPa(g))');
legend(h, lab, 'Location', 'northwest');
title('Pressure needed at the peak against \alpha over the hinge-depth band');

V.p_test = pa(1);  V.p_req = pa(2);
fprintf('Figure M.3: pressure for alpha 0.20 / 0.25 at d_h 65 mm = %.1f / %.1f kPa (report 31.9 / 39.9)\n', pa);
end

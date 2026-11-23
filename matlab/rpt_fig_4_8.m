function V = rpt_fig_4_8(p)
%RPT_FIG_4_8  Report Figure 4.8: analytical device moment against bladder pressure.
%   Model B: Mz = p x k3D(d_h), k3D over the hinge-depth band (Table 4.14, SH-C04):
%            d_h 0 / 50 / 65 / 80 mm -> 67 283 / 174 750 / 206 990 / 239 230 mm^3
%   Model A: contact forces only, 0.280 N m at 20 kPa(g), linear in p (ME-C04).
%   With the 20 kPa design point, the 27 kPa side case, the test value 6.6 N m and the
%   bound 8.25 N m. k in N m per kPa = k (mm^3) x 1e-6.
if nargin < 1 || isempty(p), p = rpt_base(); end
C = ka_colours();
MA20 = 0.280;                                   % N m at 20 kPa(g), Model A (hand calculation ME-C04)
pp = 0:1:200;                                   % kPa(g)
dh = p.k3D_band(1, :);                          % mm
kk = p.k3D_band(2, :) * 1e-6;                   % N m / kPa

order = [4 3 2 1];                              % legend order: 80, 65, 50, 0 mm
col = {[0.66 0.79 0.94], [0.36 0.60 0.88], [0.09 0.27 0.58], [0.17 0.45 0.80]};
lw  = [1.4 1.4 3.0 1.4];

figure('Name', 'Report Figure 4.8', 'Color', 'w', 'Position', [60 60 900 520]);
hold on;  grid on;  box on;
yl = [0 50];
patch([0 27 27 0], [yl(1) yl(1) yl(2) yl(2)], C.s1, 'FaceAlpha', 0.12, 'EdgeColor', 'none', 'HandleVisibility', 'off');
h = gobjects(1, 5);  lab = cell(1, 5);
for j = 1:4
    i = order(j);
    h(j) = plot(pp, kk(i) * pp, '-', 'Color', col{i}, 'LineWidth', lw(i));
    if dh(i) == 65
        lab{j} = sprintf('Model B, d_h = %d mm (design basis)', dh(i));
    else
        lab{j} = sprintf('Model B, d_h = %d mm', dh(i));
    end
end
h(5) = plot(pp, MA20 / 20 * pp, '--', 'Color', C.s2, 'LineWidth', 2.0);
lab{5} = 'Model A, contact forces only';
xline(20, ':', '20 kPa design point', 'Color', C.ink, 'LineWidth', 1.0, 'LabelVerticalAlignment', 'top', ...
      'LabelHorizontalAlignment', 'left', 'HandleVisibility', 'off');
xline(27, ':', '27 kPa side case', 'Color', C.ink, 'LineWidth', 1.0, 'LabelVerticalAlignment', 'top', ...
      'LabelHorizontalAlignment', 'right', 'HandleVisibility', 'off');
yline(8.25, '--', 'requirement 8.25 N m', 'Color', C.ink, 'LabelHorizontalAlignment', 'right', 'HandleVisibility', 'off');
yline(6.6, '--', 'test value 6.6 N m', 'Color', C.ink, 'LabelHorizontalAlignment', 'right', ...
      'LabelVerticalAlignment', 'bottom', 'HandleVisibility', 'off');
xlim([0 200]);  ylim(yl);  xticks(0:25:200);
xlabel('Bladder pressure p (kPa(g))');  ylabel('Device moment M_z (N m)');
ax = gca;
lg = legend(h, lab, 'Location', 'northwest', 'Box', 'off');
lg.Position(1) = ax.Position(1) + 0.19 * ax.Position(3);      % right of the 0-27 kPa band, as in the report
title('Analytical device moment against bladder pressure (Model B over the hinge band, Model A)');

V.Mz20 = kk * 20;   V.Mz27 = kk * 27;   V.dh = dh;
V.MA20 = MA20;
fprintf('Figure 4.8: Mz at 20 kPa = %.3f / %.3f / %.3f / %.3f N m (d_h 0/50/65/80; report 1.346/3.495/4.140/4.785)\n', V.Mz20);
fprintf('            Mz at 27 kPa = %.3f / %.3f / %.3f / %.3f N m (report 1.817/4.718/5.589/6.459)\n', V.Mz27);
end

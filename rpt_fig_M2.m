function V = rpt_fig_M2(p)
%RPT_FIG_M2  Report Figure M.2: peak device torque against alpha in the two windows,
%   with the device capability at 20 and 27 kPa(g), the test value and the requirement.
%   Window option 1: peak of alpha x tau_full over 8.43-44 % stance
%   Window option 2: peak of MIN(alpha x tau_full, MAX(M_patient, 0)) over 13-36 % stance
%   Capability: p_set x k3D = 4.14 / 5.59 N m; alpha_lim = p_set x k / tau_full (Eq. 4.12).
if nargin < 1 || isempty(p), p = rpt_base(); end
C = ka_colours();
k = p.k3D * 1e3;                                 % N m / kPa
al = 0:0.0025:0.30;
s1 = p.b3_pct;                                   % 8.43-44 %, 0.1 % grid
d1 = p.b3_def;
s2 = s1(s1 >= 13 & s1 <= 36);
d2 = d1(s1 >= 13 & s1 <= 36);
m2 = max(interp1(p.pm_pct, p.pm_Nm, s2), 0);
pk1 = al * max(d1);
pk2 = zeros(size(al));
for i = 1:numel(al)
    pk2(i) = max(min(al(i) * d2, m2));
end
Mdev = [20 27] * k;
alim = Mdev / p.def_peak;

figure('Name', 'Report Figure M.2', 'Color', 'w', 'Position', [60 60 900 480]);
hold on;  grid on;  box on;
h1 = plot(al, pk1, '--', 'Color', C.s2, 'LineWidth', 1.6);
h2 = plot(al, pk2, '-', 'Color', C.s1, 'LineWidth', 2.4);
yline(Mdev(1), '--', sprintf('device at 20 kPa(g): %.2f N m', Mdev(1)), 'Color', [0.4 0.4 0.4], ...
      'LabelHorizontalAlignment', 'left', 'HandleVisibility', 'off');
yline(Mdev(2), '--', sprintf('device at 27 kPa(g): %.2f N m', Mdev(2)), 'Color', [0.4 0.4 0.4], ...
      'LabelHorizontalAlignment', 'left', 'HandleVisibility', 'off');
xline(0.20, ':', 'test value 0.20', 'Color', [0.3 0.3 0.3], 'LabelVerticalAlignment', 'bottom', 'HandleVisibility', 'off');
xline(0.25, ':', 'requirement 0.25', 'Color', [0.3 0.3 0.3], 'LabelVerticalAlignment', 'bottom', 'HandleVisibility', 'off');
plot(alim, Mdev, 'ko', 'MarkerFaceColor', 'k', 'MarkerSize', 6, 'HandleVisibility', 'off');
text(alim(1) - 0.01, Mdev(1) - 0.55, sprintf('\\alpha_{lim} = %.3f', alim(1)), 'HorizontalAlignment', 'left');
text(alim(2) - 0.01, Mdev(2) + 0.55, sprintf('\\alpha_{lim} = %.3f', alim(2)), 'HorizontalAlignment', 'left');
xlim([0 0.30]);  ylim([0 10]);
xlabel('Assistance ratio \alpha');  ylabel('Peak device torque (N m)');
legend([h1 h2], {'Window option 1: \alpha \tau_{full}', 'Window option 2: capped at the patient''s moment'}, ...
       'Location', 'northwest');
title('Peak device torque against \alpha in the two windows');

V.alim = alim;  V.Mdev = Mdev;  V.cap_Nm = max(m2);
V.alpha_cap_starts = al(find(pk2 < pk1 - 1e-9, 1));
fprintf('Figure M.2: alpha_lim = %.3f / %.3f at 20 / 27 kPa (device %.2f / %.2f N m); window-2 peak saturates at %.2f N m (from alpha %.3f)\n', ...
        alim, Mdev, V.cap_Nm, V.alpha_cap_starts);
end

function V = rpt_fig_4_2(p)
%RPT_FIG_4_2  Report Figure 4.2: required assistive torque over stance at two months
%   for alpha = 0.10, 0.20 and 0.25 (window option 1) and alpha = 0.20 capped at the
%   patient's own moment (window option 2).
%
%   Window option 1: tau = alpha x tau_full(t),                       8.43-44 % stance
%   Window option 2: tau = MIN(alpha x tau_full(t), M_patient(t)),     13-36 % stance
%   tau_full and M_patient are Basem's O1 v10 / O2 v3 curves (data\*.csv, ka_gait_data).
%   The legend quotes alpha x 33 N m (the report's reference torques 6.60 / 8.25 N m).
if nargin < 1 || isempty(p), p = rpt_base(); end
C = ka_colours();

% stance grid with both sides of every window edge, so the steps are drawn vertical
e = 1e-6;
s = unique([0:0.05:100, 8.43 - e, 8.43, 44, 44 + e, 13 - e, 13, 36, 36 + e]);
t = s / 100 * p.T_stance;

q1 = ka_set_window(p, 1);                 % window option 1, no cap
q2 = ka_set_window(p, 2);                 % window option 2, capped at the patient
alphas = [0.10 0.20 0.25];
tq1 = zeros(numel(alphas), numel(s));
for i = 1:numel(alphas)
    q1.alpha = alphas(i);
    tq1(i, :) = ka_torque_req(q1, t);
end
q2.alpha = 0.20;
tq2 = ka_torque_req(q2, t);

col1 = {[0.62 0.79 0.90], [0.16 0.45 0.71], [0.06 0.17 0.42]};   % light, mid, dark blue
lw1  = [1.2 2.0 1.4];
cg   = [0.17 0.60 0.20];                                         % window 2 (green)
lab1 = {sprintf('\\alpha = 0.10, Option 1'), ...
        sprintf('\\alpha = 0.20, Option 1 (test value, peak %.2f N m)', 0.20 * p.def_peak), ...
        sprintf('\\alpha = 0.25, Option 1 (bound, peak %.2f N m)', 0.25 * p.def_peak)};

figure('Name', 'Report Figure 4.2', 'Color', 'w', 'Position', [60 60 1000 520]);
hold on;  grid on;  box on;
yl = [0 9];
hw1 = patch([8.43 44 44 8.43], [yl(1) yl(1) yl(2) yl(2)], C.s1, 'FaceAlpha', 0.16, 'EdgeColor', 'none');
hw2 = patch([13 36 36 13], [yl(1) yl(1) yl(2) yl(2)], cg, 'FaceAlpha', 0.28, 'EdgeColor', 'none');
h = gobjects(1, 4);
for i = 1:3
    h(i) = plot(s, tq1(i, :), '-', 'Color', col1{i}, 'LineWidth', lw1(i));
end
h(4) = plot(s, tq2, '--', 'Color', cg, 'LineWidth', 1.6);
xlim([0 100]);  ylim(yl);  xticks(0:10:100);
xlabel('Stance (%)');  ylabel('Required assistive torque (N m)');
legend([h(1) h(2) h(3) h(4) hw1 hw2], [lab1, {'\alpha = 0.20, Option 2 (capped at the patient''s moment)', ...
       'Window Option 1: 8.43-44 % stance', 'Window Option 2: 13-36 % stance'}], ...
       'Location', 'northoutside', 'NumColumns', 3, 'Box', 'off');
title('Required assistive torque over stance at two months (70 kg, 1.70 m)');

V.peak_opt1 = max(tq1, [], 2)';            % N m, alpha 0.10 / 0.20 / 0.25
V.peak_opt2 = max(tq2);
V.onset_opt1_a020 = 0.20 * interp1(p.b3_pct, p.b3_def, 8.43);
V.offset_opt1_a020 = 0.20 * interp1(p.b3_pct, p.b3_def, 44);
fprintf('Figure 4.2: peak Option 1 = %.2f / %.2f / %.2f N m (alpha 0.10 / 0.20 / 0.25; report 3.30 / 6.60 / 8.25 on 33 N m)\n', V.peak_opt1);
fprintf('            peak Option 2 (alpha 0.20, capped) = %.2f N m; Option 1 step %.2f N m at 8.43 %%, %.2f N m at 44 %%\n', ...
        V.peak_opt2, V.onset_opt1_a020, V.offset_opt1_a020);
end

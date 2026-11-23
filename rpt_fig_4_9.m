function V = rpt_fig_4_9(p)
%RPT_FIG_4_9  Report Figure 4.9: window option 2 at the 20 kPa(g) design point.
%   Top:    patient's own extension moment, demand at the test value alpha = 0.20
%           (uncapped) and the device at 20 kPa(g), alpha = 0.125 (capped):
%           tau_req = MIN(alpha x tau_full, MAX(M_patient, 0)), 13-36 % stance (Eq. 4.14)
%   Bottom: bladder pressure the device must follow, p = tau_req / k (k3D, 0.207 N m/kPa)
%   Frame by frame on Basem's 1 % stance frames (1 % = 7.05 ms); shaded where the cap acts.
if nargin < 1 || isempty(p), p = rpt_base(1, 2); end
p = ka_set_window(p, 2);
p = ka_set_option(p, 1);
p = ka_derived(p);
C = ka_colours();
k = p.k_Nm_per_kPa;

s  = 13:36;                                                % % stance, Basem's frames
tf = interp1(p.b3_pct, p.b3_def, s);                       % tau_full (N m)
mp = interp1(p.pm_pct, p.pm_Nm, s);                        % patient's own moment (N m)
dev = min(p.alpha * tf, max(mp, 0));                       % device torque (N m)
pb  = dev / k;                                             % bladder pressure (kPa(g))
capped = p.alpha * tf > mp;
sf  = 13:0.1:36;                                           % smooth demand curve
dem = 0.20 * interp1(p.b3_pct, p.b3_def, sf);

grey = [0.94 0.93 0.91];
figure('Name', 'Report Figure 4.9', 'Color', 'w', 'Position', [60 60 900 640]);
tl = tiledlayout(5, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

ax1 = nexttile(tl, [3 1]);  hold(ax1, 'on');  grid(ax1, 'on');  box(ax1, 'on');
cap_shade(ax1, s, capped, [0 10.5], grey, true);
h1 = plot(ax1, s, mp, '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.4);
h2 = plot(ax1, sf, dem, '--', 'Color', C.s2, 'LineWidth', 1.4);
h3 = plot(ax1, s, dev, '-o', 'Color', C.s1, 'LineWidth', 2.2, 'MarkerSize', 4, 'MarkerFaceColor', C.s1);
xlim(ax1, [12.6 36.4]);  ylim(ax1, [0 10.5]);  ylabel(ax1, 'Moment (N m)');
legend(ax1, [h1 h2 h3], {'Patient''s own extension moment', ...
       'Demand at the test value \alpha = 0.20 (uncapped)', ...
       sprintf('Device at 20 kPa(g), \\alpha = %.3f (capped)', p.alpha)}, 'Location', 'south', 'Box', 'off');
title(ax1, 'Window Option 2 at the 20 kPa(g) design point');
set(ax1, 'XTickLabel', []);

ax2 = nexttile(tl, [2 1]);  hold(ax2, 'on');  grid(ax2, 'on');  box(ax2, 'on');
cap_shade(ax2, s, capped, [0 24], grey, false);
yline(ax2, p.cap_kPa, '--', '20 kPa design point', 'Color', [0.6 0.6 0.6], 'LabelHorizontalAlignment', 'right');
plot(ax2, s, pb, '-o', 'Color', C.s1, 'LineWidth', 2.2, 'MarkerSize', 4, 'MarkerFaceColor', C.s1);
xlim(ax2, [12.6 36.4]);  ylim(ax2, [0 24]);
ylabel(ax2, 'Bladder pressure (kPa(g))');
xlabel(ax2, 'Stance (%); window option 2, 13-36 % (1 % = 7.05 ms)');
linkaxes([ax1 ax2], 'x');

[~, ipk] = max(pb);
dpdt = diff(pb) / (0.01 * p.T_stance);                     % kPa/s between frames
V.alpha = p.alpha;  V.s = s;  V.p_kPa = pb;  V.dev_Nm = dev;  V.capped_pct = s(capped);
V.p_onset = pb(1);  V.p_peak = pb(ipk);  V.t_peak_ms = s(ipk) / 100 * p.T_stance * 1e3;  V.p_offset = pb(end);
V.rise_kPa_s = max(dpdt);  V.fall_kPa_s = -min(dpdt);
fprintf('Figure 4.9: alpha %.4f; pressure %.2f kPa at the onset (%.0f ms), %.2f kPa at %.0f ms, %.2f kPa at the offset (%.0f ms)\n', ...
        V.alpha, V.p_onset, 13/100*p.T_stance*1e3, V.p_peak, V.t_peak_ms, V.p_offset, 36/100*p.T_stance*1e3);
fprintf('            steepest rise %.0f kPa/s, fall %.0f kPa/s (report 864 / 592); cap acts at %s %% stance\n', ...
        V.rise_kPa_s, V.fall_kPa_s, mat2str(V.capped_pct));
end

function cap_shade(ax, s, capped, yl, c, lab)
% shade +/- 0.5 % around each capped frame, clipped to 13-36 %; one label per run
i = 1;
while i <= numel(s)
    if capped(i)
        j = i;
        while j < numel(s) && capped(j + 1), j = j + 1; end
        x0 = max(s(i) - 0.5, s(1) - 0.4);  x1 = min(s(j) + 0.5, s(end) + 0.4);
        patch(ax, [x0 x1 x1 x0], [yl(1) yl(1) yl(2) yl(2)], c, 'EdgeColor', 'none', 'HandleVisibility', 'off');
        if lab
            text(ax, (x0 + x1) / 2, yl(2) * 0.97, 'cap acts', 'HorizontalAlignment', 'center', ...
                 'VerticalAlignment', 'top', 'FontSize', 8, 'Color', [0.35 0.35 0.35]);
        end
        i = j + 1;
    else
        i = i + 1;
    end
end
end

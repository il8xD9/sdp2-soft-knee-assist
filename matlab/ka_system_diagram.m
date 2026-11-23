function ka_system_diagram()
%KA_SYSTEM_DIAGRAM  Structure of the pneumatic system (one leg): air path, power, signals.
%   Draws results\fig19_system_structure.png. Values are those of the model runs
%   (one MHJ10, two MHE3 at the port, no relief valve).
air = [0.16 0.47 0.85];  pwr = [0.91 0.40 0.20];  sig = [0.15 0.55 0.40];
fa = [0.93 0.96 1.00];  fp = [1.00 0.95 0.93];  fs = [0.92 0.96 0.94];
f = figure('Color', 'w', 'Position', [40 40 1500 870], 'Visible', 'off');
ax = axes(f, 'Position', [0 0 1 1]);  hold(ax, 'on');  axis(ax, [-10 2000 -20 1160]);  axis(ax, 'off');
set(ax, 'YDir', 'reverse');
text(ax, 45, 30, 'Pneumatic system (one leg) - air path (blue), electrical power (orange), signals (green)', ...
     'FontSize', 13, 'FontWeight', 'bold', 'Color', [0.15 0.15 0.15], 'Interpreter', 'none');
B = @(x, y, w, h, ttl, body, ec, fc, ls) box(ax, x, y, w, h, ttl, body, ec, fc, ls);
B(40, 110, 230, 150, 'Pump', {'KNF NMP 850.1.2 HP', '15 l/min, 2.2 bar(g)', 'switched 55 / 70 kPa(g)'}, air, fa, '-');
B(330, 110, 230, 150, 'Receiver 1.5 L', {'check valve, bypass relief', 'receiver relief <= 1.5 bar(g)'}, air, fa, '-');
B(620, 110, 260, 150, '1 x MHJ10 (NC)', {'inlet', 'C 0.66 l/(s bar), b 0.36', 'open 1.0 / close 0.5 ms'}, air, fa, '-');
B(940, 110, 200, 150, 'Tube', {'PEN-6x1', '4 mm x 80 mm', 'K = 1.5'}, air, fa, '-');
B(1200, 100, 330, 170, 'Bladder actuator', {'391.9 mL with tube', 'k3D = 0.207 N m/kPa', '4.14 / 5.59 N m at 20 / 27 kPa'}, air, fa, '-');
B(1590, 110, 360, 150, '2 x MHE3 (NO) at the port', {'exhausts, port 3 sealed', 'C 0.82 l/(s bar) each (b 0.36)', '0.44 l/s at 2.4 kPa -> silencer'}, air, fa, '-');
B(1235, 300, 260, 120, 'Relief valve L500', {'not fitted', '(considered, not adopted)'}, [0.55 0.55 0.55], [0.96 0.96 0.96], '--');
arrow(ax, [270 330], [185 185], air);  arrow(ax, [560 620], [185 185], air);  arrow(ax, [880 940], [185 185], air);
arrow(ax, [1140 1200], [185 185], air);  arrow(ax, [1530 1590], [185 185], air);
arrow(ax, [1770 1770], [260 300], air);  text(ax, 1788, 278, 'to air', 'Color', air, 'FontSize', 10);
plot(ax, [1365 1365], [270 300], ':', 'Color', [0.55 0.55 0.55], 'LineWidth', 1.5);

B(40, 470, 330, 140, 'Footswitches (2)', {'heel + 1st metatarsal head', '100 Hz filter, read at 1 kHz', 'detection 1.6-9.6 ms'}, sig, fs, '-');
B(470, 450, 620, 200, 'Controller (microcontroller, 1 kHz)', {'contact rules G-1..G-5, window clock (detection - 5.6 ms)', ...
  'window 2: 13-36 % stance, request MIN(alpha tau_full, patient moment)', 'PI + feedforward + anti-windup, kp 0.30, ki 1.5, PWM 200 Hz', ...
  'set point 20 kPa (design), 27 kPa (side case)'}, sig, fs, '-');
B(1200, 470, 330, 120, '2 x MP3V5050GP', {'bladder pressure, 0-50 kPa', '+/-1.25 kPa, 1.0 ms'}, sig, fs, '-');
arrow(ax, [370 470], [540 540], sig);  arrow(ax, [1200 1090], [520 520], sig);
plot(ax, [1530 1560 1560 1530], [230 230 530 530], '-', 'Color', sig, 'LineWidth', 1.5);

B(470, 720, 300, 130, 'Trip comparator', {'own sensor, no software', '22.6 / 29.6 kPa(g)'}, pwr, fp, '-');
B(820, 720, 270, 130, 'Watchdog', {'Maxim MAX6369', '10 ms (30 ms worst)'}, pwr, fp, '-');
plot(ax, [1365 1365 620 620], [590 690 690 715], '-', 'Color', sig, 'LineWidth', 1.3);
plot(ax, [955 955], [650 715], '-', 'Color', sig, 'LineWidth', 1.3);
text(ax, 968, 685, 'heartbeat', 'Color', sig, 'FontAngle', 'italic', 'FontSize', 10);
text(ax, 1250, 676, 'trip sensor', 'Color', sig, 'FontAngle', 'italic', 'FontSize', 10);

B(40, 900, 330, 200, 'Battery 7S1P', {'Samsung INR18650-25R', '25.2 V, 63 Wh', 'BQ76930 protection + fuse'}, pwr, fp, '-');
B(470, 920, 300, 160, 'Regulator 24 V', {'TI LM5176 buck-boost', '>= 85 W (51.2 W peak)'}, pwr, fp, '-');
B(840, 920, 360, 160, '2 x 2 ST IPS160H', {'high-side switches in series', '(trip, watchdog); valves split', 'over two pairs (2.7 A peak)'}, pwr, fp, '-');
B(1300, 920, 650, 160, 'Valve and pump power (24 V)', {'drives the pump, the one MHJ10 and the two MHE3', ...
  'opening either switch: inlet shut, both exhausts open, pump stops', ...
  '-> the bladder vents (power loss: 81 / 100 ms from 20 / 27 kPa)'}, pwr, fp, '-');
arrow(ax, [370 470], [1000 1000], pwr);  arrow(ax, [770 840], [1000 1000], pwr);  arrow(ax, [1200 1300], [1000 1000], pwr);
plot(ax, [620 935], [850 918], '-', 'Color', pwr, 'LineWidth', 1.3);
plot(ax, [955 1000], [850 918], '-', 'Color', pwr, 'LineWidth', 1.3);
here = fileparts(mfilename('fullpath'));
exportgraphics(f, fullfile(here, 'results', 'fig19_system_structure.png'), 'Resolution', 150);
close(f);
end

function box(ax, x, y, w, h, ttl, body, ec, fc, ls)
rectangle(ax, 'Position', [x y w h], 'EdgeColor', ec, 'FaceColor', fc, 'LineWidth', 2, 'LineStyle', ls);
text(ax, x + w/2, y + 22, ttl, 'HorizontalAlignment', 'center', 'FontWeight', 'bold', 'FontSize', 12, 'Color', [0.15 0.15 0.15]);
n = numel(body);  y0 = y + h/2 + 18 - (n - 1) * 10;
for i = 1:n
    text(ax, x + w/2, y0 + (i - 1) * 20, body{i}, 'HorizontalAlignment', 'center', 'FontSize', 10, 'Color', [0.2 0.2 0.2], 'Interpreter', 'none');
end
end

function arrow(ax, xs, ys, c)
plot(ax, xs, ys, '-', 'Color', c, 'LineWidth', 2.5);
d = [xs(2) - xs(1), ys(2) - ys(1)];  d = d / norm(d);  n = [-d(2) d(1)];  L = 16;  W = 8;
tip = [xs(2) ys(2)];  b = tip - L * d;
patch(ax, [tip(1) b(1) + W*n(1) b(1) - W*n(1)], [tip(2) b(2) + W*n(2) b(2) - W*n(2)], c, 'EdgeColor', c);
end

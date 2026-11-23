%KA_QUICK_DEMO  First test: one stride at the design alpha for the Rev 27 DESIGN SYSTEM:
%   design point 20 kPa(g), window option 2 (13-36 % stance, capped at the
%   patient's moment), ONE MHJ10 inlet, two MHE3 at the bladder port,
%   3D torque constant 0.207 N m/kPa. About 1-2 min (most of it the tables
%   and the fill-timing search). Prints the N1 / N4 numbers and plots pressure,
%   reference, duty and valve states.
here = fileparts(mfilename('fullpath'));  addpath(here);
p = ka_setup(1, 1, 2);
ka_print_hardware(p);
cfg = ka_default_cfg('pulse', 'demand', 'n_exh', p.n_exh_sys, 'exh_at_port', true, ...
                     'adiabatic', false, 'pr_kPa', 53, 't_end', 0.66);
tic;  r = ka_simulate(p, cfg);  t_run = toc;
m = ka_metrics_demand(p, r);
fprintf('%s, %s, %d MHJ10: alpha %.4f, set point %.0f kPa(g), G-5 floor %.2f ms, fill command %.2f ms (%.1f s run)\n', ...
        p.opt_name, p.win_name, p.n_in, p.alpha, p.cap_kPa, p.fill_floor*1e3, r.t_fill_w*1e3, t_run);
fprintf('   at the onset %.1f %%, before %.2f %%, missing %.2f %%, peak %.2f kPa, back at 2.4 kPa(g) at %.1f ms\n', ...
        m.onset_pct, m.before_pct, m.missing_pct, m.peak_kPa, m.back_rest_ms);

figure('Name', 'Quick demo (Rev 27)', 'Color', 'w', 'Position', [60 60 900 650]);
subplot(3, 1, 1);  hold on;  grid on;
plot(r.log.t*1e3, r.log.p, 'b', 'LineWidth', 1.4);
plot(r.log.t*1e3 - p.sens_delay*1e3, r.log.r, 'k--');
tg = (0:0.25:400)/1e3;  dem = min(ka_torque_req(p, tg)/p.k_Nm_per_kPa, p.cap_kPa);  dem(dem<=0) = NaN;
plot(tg*1e3, dem, 'r:');
yline(p.cap_kPa, ':', 'set point');  xlim([0 400]);
ylabel('kPa(g)');  title(sprintf('%s, %s, %d MHJ10: bladder (blue), reference (dashed), asked (red)', p.opt_name, p.win_name, p.n_in));
subplot(3, 1, 2);  grid on;
plot(r.log.t*1e3, r.log.u);  xlim([0 400]);  ylim([-1.1 1.1]);  ylabel('duty u');
subplot(3, 1, 3);  hold on;  grid on;
plot(r.log.t*1e3, r.log.inopen, 'g');  plot(r.log.t*1e3, r.log.exopen / 5 + 1.2, 'r');
xlim([0 400]);  ylim([-0.1 2.4]);  xlabel('time after contact (ms)');
ylabel('valves');  legend('inlet open', 'exhausts open (count/5 + 1.2)', 'Location', 'east');

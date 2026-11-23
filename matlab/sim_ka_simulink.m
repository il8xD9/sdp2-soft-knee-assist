function out = sim_ka_simulink(p, pulse, adiabatic, pr_kPa, tag)
%SIM_KA_SIMULINK  Runs the Simulink model and checks it against the script model.
%   sim_ka_simulink                       DESIGN SYSTEM: 20 kPa, window 2, one MHJ10,
%                                         two MHE3, demand pulse, room temp., receiver 53
%   sim_ka_simulink(p, 'bounding', true, 70, 'P27')   p from ka_setup / ka_case with its
%                                         fill timing (ka_fill_timing)
%   Builds knee_assist_rev27.slx if it is missing, runs one stride (0.66 s),
%   runs ka_simulate with the same settings, overlays both and prints the
%   largest difference. Both call the same ka_logic_step and ka_plant_deriv.
if nargin < 1 || isempty(p), p = ka_setup(1, 1, 2); end
if nargin < 2 || isempty(pulse), pulse = 'demand'; end
if nargin < 3 || isempty(adiabatic), adiabatic = false; end
if nargin < 4 || isempty(pr_kPa), pr_kPa = 53; end
if nargin < 5 || isempty(tag), tag = sprintf('%s_%s_in%d', p.opt_short, p.win_short, p.n_in); end
mdl = 'knee_assist_rev27';
here = fileparts(mfilename('fullpath'));

cfg = ka_default_cfg('pulse', pulse, 'n_exh', p.n_exh_sys, 'exh_at_port', true, ...
                     'adiabatic', adiabatic, 'pr_kPa', pr_kPa, 't_end', 0.66);
ka_simulink_setup(p, cfg);
if ~exist(fullfile(here, [mdl '.slx']), 'file'), build_ka_simulink(mdl); end
if ~bdIsLoaded(mdl), load_system(fullfile(here, [mdl '.slx'])); end

fprintf('Simulink run (%s, %s, %d MHJ10, %s pulse) ... ', p.opt_name, p.win_name, p.n_in, pulse);  tic;
so = sim(mdl, 'ReturnWorkspaceOutputs', 'on');
t_sl = toc;  fprintf('%.1f s\n', t_sl);
g  = @(n) squeeze(so.get(n));
sl.t = g('sl_t');  sl.p = g('sl_p');  sl.r = g('sl_r');  sl.u = g('sl_u');
sl.inopen = g('sl_inopen');  sl.pr = g('sl_pr');  sl.stage = g('sl_stage');  sl.T = g('sl_T');

fprintf('Script run ... ');  tic;
res = ka_simulate(p, cfg);
t_sc = toc;  fprintf('%.1f s\n', t_sc);

n = min(numel(sl.t), numel(res.log.t));
d = max(abs(sl.p(1:n) - res.log.p(1:n)));
fprintf('Largest difference Simulink - script: %.4g kPa over %d steps\n', d, n);
m_sl = ka_metrics_demand(p, struct('log', struct('t', sl.t(1:n), 'p', sl.p(1:n)), 'cfg', cfg));
m_sc = ka_metrics_demand(p, res);

C = ka_colours();
figure('Name', 'Simulink vs script', 'Color', 'w', 'Position', [60 60 1050 520]);
subplot(3,1,[1 2]);  hold on;  grid on;
plot(res.log.t*1e3, res.log.p, 'LineWidth', 3, 'Color', [0.72 0.82 1]);
plot(sl.t*1e3, sl.p, '--', 'Color', C.s1, 'LineWidth', 1.2);
plot(sl.t*1e3, sl.r, ':', 'Color', C.ink, 'LineWidth', 1.2);
if strcmp(pulse, 'demand')
    tg = (0:0.25:400)/1e3;  dem = min(ka_torque_req(p, tg)/p.k_Nm_per_kPa, p.cap_kPa);  dem(dem<=0) = NaN;
    plot(tg*1e3, dem, '-', 'Color', C.s2, 'LineWidth', 1.0);
    legend('script ka\_simulate', 'Simulink knee\_assist\_rev27', 'controller reference r', 'asked \tau_{req}/k', 'Location', 'northeast');
else
    legend('script ka\_simulate', 'Simulink knee\_assist\_rev27', 'controller reference r', 'Location', 'northeast');
end
xlim([0 450]);  ylabel('bladder (kPa(g))');
title(sprintf('%s, %s, %d MHJ10, two MHE3, %s pulse: Simulink vs script (max diff. %.3g kPa)', ...
      p.opt_name, p.win_name, p.n_in, pulse, d));
subplot(3,1,3);  grid on;  hold on;
plot(sl.t*1e3, sl.u, 'Color', C.s1);  plot(sl.t*1e3, sl.inopen, 'Color', C.s3);
xlim([0 450]);  ylim([-1.1 1.1]);  ylabel('duty u / inlet open');  xlabel('time after contact (ms)');
legend('duty u (Simulink)', 'inlet open (Simulink)', 'Location', 'southeast');
ka_savefig(['fig14_simulink_vs_script_' tag]);
out = struct('sl', sl, 'script', res, 'max_diff_kPa', d, 'm_sl', m_sl, 'm_sc', m_sc, 't_sl', t_sl, 't_sc', t_sc);
end

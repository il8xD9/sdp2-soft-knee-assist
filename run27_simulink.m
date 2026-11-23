function R = run27_simulink(P)
%RUN27_SIMULINK  Builds knee_assist_rev27.slx, prints its diagrams and checks it
%   against the script model for the design system (20 kPa, window 2, one MHJ10,
%   two MHE3) and the 27 kPa side case. P = R.p from run27_n1_n4.
fprintf('\n===== Simulink model knee_assist_rev27 =====\n');
here = fileparts(mfilename('fullpath'));
mdl = 'knee_assist_rev27';
ka_simulink_setup(P{1,1,2});
build_ka_simulink(mdl);
load_system(fullfile(here, [mdl '.slx']));
d = fullfile(here, 'results');
try
    print(['-s' mdl], '-dpng', '-r150', fullfile(d, 'fig15_simulink_top.png'));
    subs = {'Controller board', 'Valves', 'Pneumatic plant'};
    fn = {'fig16_simulink_controller', 'fig17_simulink_valves', 'fig18_simulink_plant'};
    for i = 1:3
        print(['-s' mdl '/' subs{i}], '-dpng', '-r150', fullfile(d, [fn{i} '.png']));
    end
    fprintf('Simulink diagrams printed\n');
catch err
    fprintf('Diagram print failed: %s\n', err.message);
end
R = struct();
o = sim_ka_simulink(P{1,1,2}, 'demand', false, 53, 'P20_W2_in1');
ka_report('add', 'SL.diff.P20', 'Simulink against the script, 20 kPa, W2, one MHJ10: largest difference', o.max_diff_kPa, 0, 'kPa');
ka_report('add', 'SL.on.P20.sl', 'Simulink: at the onset (slowest case)', o.m_sl.onset_pct, o.m_sc.onset_pct, '%');
ka_report('add', 'SL.mis.P20.sl', 'Simulink: missing in the window', o.m_sl.missing_pct, o.m_sc.missing_pct, '%');
ka_report('add', 'SL.back.P20.sl', 'Simulink: back at 2.4 kPa', o.m_sl.back_rest_ms, o.m_sc.back_rest_ms, 'ms');
ka_report('add', 'SL.time.P20', 'Simulink run time for one stride (0.66 s)', o.t_sl, NaN, 's');
R.o20 = o;
close all
o = sim_ka_simulink(P{1,2,2}, 'demand', false, 53, 'P27_W2_in1');
ka_report('add', 'SL.diff.P27', 'Simulink against the script, 27 kPa, W2, one MHJ10: largest difference', o.max_diff_kPa, 0, 'kPa');
ka_report('add', 'SL.pk.P27.sl', 'Simulink: peak pressure, 27 kPa', o.m_sl.peak_kPa, o.m_sc.peak_kPa, 'kPa');
R.o27 = o;
close all
save_system(mdl);
close_system(mdl, 0);
end

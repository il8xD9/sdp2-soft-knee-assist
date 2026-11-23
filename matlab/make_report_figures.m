function T = make_report_figures(mode, show)
%MAKE_REPORT_FIGURES  The pneumatic and analytical graphs of the SDP-II final report,
%   made by the Rev 27 MATLAB / Simulink model and saved under their report numbers in
%   results\report_figures\ (Figure_6_7.png, Figure_6_7.fig, ...).
%
%   make_report_figures                 'quick' (about 1 min): draws the analytical figures
%                                       4.2, 4.8, 4.9, 6.10, M.2, M.3, M.4 and the system
%                                       diagram 4.10, and copies the simulation figures of
%                                       the last run_all_rev27 from results\ under the
%                                       report numbers
%   make_report_figures('simulink')     as 'quick', and first rebuilds knee_assist_rev27.slx
%                                       and re-runs the Simulink check against the script
%                                       (Figures 5.5, 5.6, M.6-M.9), about 5-15 min
%   make_report_figures('full')         runs run_all_rev27 first (about 1-1.5 h): every
%                                       simulation figure is made again, then as 'quick'
%   make_report_figures(mode, true)     also opens every report figure on screen
%   T = make_report_figures(...)        table: report figure, caption, file, source, status
%                                       (also written to report_figure_index.csv)
%
%   Report figure  <- package output
%     4.2, 4.8, 4.9, 6.10, M.2, M.3, M.4   rpt_fig_*.m (analytical, gait data, k3D band)
%     4.10  fig19 (ka_system_diagram)      5.4  fig01 (run27_inputs)
%     5.5   fig15 (run27_simulink)         5.6  fig14 ..._P20_W2_in1 (sim_ka_simulink)
%     6.7   fig08 (run27_n1_n4)            6.8  fig11 (run27_n1_n4)
%     6.9   fig05 (run27_n2_n3)            6.11 fig07 (run27_n5)
%     6.12  fig13 (run27_n7)               M.5  fig04 (run27_n2_n3)
%     M.6-M.8 fig16-18 (Simulink diagrams) M.9  fig14 ..._P27_W2_in1
%     M.11  fig06 (run27_n5)               M.12 fig09 (run27_n1_n4)
%     M.13  fig12 (run27_n6)               M.14 fig10 (run27_n1_n4)
%   Not made by this model (no data in the package): 4.1, 4.3 and M.1 (healthy and ACLR
%   moments and knee angle, Bittner et al. digitised), 4.4-4.7 (CAD), 5.1-5.3, 6.1-6.6,
%   7.1 and M.10 (OpenSim / FEA), 6.13 (evidence chain), M.15 (earlier Simulink layout).
%
%   Hardware values: see ka_params.m.

if nargin < 1 || isempty(mode), mode = 'quick'; end
if nargin < 2 || isempty(show), show = false; end
mode = lower(char(mode));
if ~ismember(mode, {'quick', 'simulink', 'full'})
    error('make_report_figures: mode must be ''quick'', ''simulink'' or ''full''');
end
here = fileparts(mfilename('fullpath'));
addpath(here);
res = fullfile(here, 'results');
if ~exist(res, 'dir'), mkdir(res); end
out = rpt_folder();
old_vis = get(0, 'DefaultFigureVisible');
restore = onCleanup(@() set(0, 'DefaultFigureVisible', old_vis));
set(0, 'DefaultFigureVisible', 'off');
t0 = tic;
fprintf('\n===== Report figures (SDP-II final report) from the Rev 27 model, mode ''%s'' =====\n', mode);

%% ---- 1. simulation runs (optional) ----
switch mode
    case 'full'
        fprintf('Running run_all_rev27 (about 1-1.5 h) ...\n');
        run_full();
    case 'simulink'
        fprintf('Rebuilding knee_assist_rev27.slx and running Simulink against the script ...\n');
        run_simulink_only();
end
close all

%% ---- 2. analytical figures (drawn here) ----
p = rpt_base(1, 2);                      % 20 kPa, window option 2, gait data, k3D
fprintf('Design point: k = %.4f N m/kPa, alpha = %.4f, onset demand %.2f kPa(g)\n', ...
        p.k_Nm_per_kPa, p.alpha, p.p_on_kPa);
ana = {'Figure_4_2',  @rpt_fig_4_2;
       'Figure_4_8',  @rpt_fig_4_8;
       'Figure_4_9',  @rpt_fig_4_9;
       'Figure_6_10', @rpt_fig_6_10;
       'Figure_M_2',  @rpt_fig_M2;
       'Figure_M_3',  @rpt_fig_M3;
       'Figure_M_4',  @rpt_fig_M4};
made = {};
for i = 1:size(ana, 1)
    try
        ana{i, 2}(p);
        rpt_savefig(ana{i, 1});
        close(gcf);
        made{end+1} = ana{i, 1}; %#ok<AGROW>
    catch err
        fprintf(2, '%s failed: %s\n', ana{i, 1}, err.message);
        close all
    end
end
try
    ka_system_diagram();                 % results\fig19_system_structure.png (Figure 4.10)
    close all
catch err
    fprintf(2, 'ka_system_diagram failed: %s (the last fig19 is used)\n', err.message);
end

%% ---- 3. report figure <- package output ----
M = figure_map();
n = size(M, 1);
status = cell(n, 1);  file = cell(n, 1);
for i = 1:n
    name = strrep(strrep(M{i, 1}, 'Figure ', 'Figure_'), '.', '_');
    file{i} = [name '.png'];
    src = M{i, 3};
    if strcmp(src, 'rpt')
        if ismember(name, made), status{i} = 'drawn'; else, status{i} = 'FAILED'; end
        continue
    end
    s_png = fullfile(res, [src '.png']);
    s_fig = fullfile(res, [src '.fig']);
    if exist(s_png, 'file')
        copyfile(s_png, fullfile(out, file{i}));
        if exist(s_fig, 'file'), copyfile(s_fig, fullfile(out, [name '.fig'])); end
        d = dir(s_png);
        status{i} = ['copied, run of ' char(datetime(d.datenum, 'ConvertFrom', 'datenum', 'Format', 'yyyy-MM-dd HH:mm'))];
    else
        status{i} = sprintf('MISSING: run %s (or make_report_figures(''full''))', M{i, 4});
    end
end
Report = M(:, 1);  Caption = M(:, 2);  Source = M(:, 3);  Made_by = M(:, 4);  File = file;  Status = status;
T = table(Report, Caption, File, Source, Made_by, Status);
writetable(T, fullfile(out, 'report_figure_index.csv'));

fprintf('\n%-12s %-46s %s\n', 'Report', 'File', 'Status');
for i = 1:n
    fprintf('%-12s %-46s %s\n', T.Report{i}, fullfile('results', 'report_figures', T.File{i}), T.Status{i});
end
fprintf(['\nNot made by this model (no data in the package): 4.1, 4.3, M.1 (healthy / ACLR curves),\n' ...
         '4.4-4.7 (CAD), 5.1-5.3, 6.1-6.6, 7.1, M.10 (OpenSim / FEA), 6.13, M.15.\n']);
fprintf('Done in %.1f min. Index: results\\report_figures\\report_figure_index.csv\n', toc(t0) / 60);

%% ---- 4. show ----
if show
    set(0, 'DefaultFigureVisible', 'on');
    for i = 1:n
        f_fig = fullfile(out, strrep(T.File{i}, '.png', '.fig'));
        f_png = fullfile(out, T.File{i});
        if exist(f_fig, 'file')
            h = openfig(f_fig, 'new', 'visible');
            set(h, 'Name', [T.Report{i} ': ' T.Caption{i}], 'NumberTitle', 'off');
        elseif exist(f_png, 'file')
            figure('Name', [T.Report{i} ': ' T.Caption{i}], 'NumberTitle', 'off', 'Color', 'w');
            image(imread(f_png));  axis image off;
        end
    end
end
end

%% =====================================================================
function run_full()
% run_all_rev27 is a script: run it here so its variables stay out of the caller
run_all_rev27;
end

function run_simulink_only()
% Simulink check of run_all_rev27 without the N1-N7 runs: same inputs as R14.p{1, pc, 2}
ka_report('reset');
base = ka_setup(1, 1, 2, 'timing', false);
P = cell(2, 2, 2);
for pc = 1:2
    q = ka_case(base, pc, 2);
    [q.fill_floor, q.t_fill_demand] = ka_fill_timing(q);
    P{1, pc, 2} = q;
end
run27_simulink(P);
end

function M = figure_map()
% report figure | caption | package output in results\ ('rpt' = drawn here) | made by
M = {
'Figure 4.2',  'Required assistive torque over stance at two months, alpha 0.10 / 0.20 / 0.25 (Option 1) and 0.20 capped (Option 2)', 'rpt', 'rpt_fig_4_2';
'Figure 4.8',  'Analytical device moment against bladder pressure', 'rpt', 'rpt_fig_4_8';
'Figure 4.9',  'Window Option 2 at the 20 kPa(g) design point', 'rpt', 'rpt_fig_4_9';
'Figure 4.10', 'Structure of the pneumatic system for one leg: air path, electrical power and signals', 'fig19_system_structure', 'ka_system_diagram';
'Figure 5.4',  'Inputs of the pneumatic model from the clinical constraints', 'fig01_basem_inputs', 'run27_inputs';
'Figure 5.5',  'Simulink model of the pneumatic system, top level', 'fig15_simulink_top', 'run27_simulink';
'Figure 5.6',  'Simulink against the script model, Option B at 20 kPa(g), window Option 2', 'fig14_simulink_vs_script_P20_W2_in1', 'run27_simulink';
'Figure 6.7',  'Window Option 2: bladder pressure following the demand with one inlet valve (Option B), fastest case', 'fig08_demand_pulses_w2', 'run27_n1_n4';
'Figure 6.8',  'Pressure-equivalent moment (k x pressure, one inlet valve, slowest case) against the requested torque', 'fig11_device_torque', 'run27_n1_n4';
'Figure 6.9',  'Bounding pulse over one stride at 20 and 27 kPa(g), window Option 2', 'fig05_bounding_pulse', 'run27_n2_n3';
'Figure 6.10', 'Swing squeeze with two exhaust valves at the bladder port', 'rpt', 'rpt_fig_6_10';
'Figure 6.11', 'FS-3: peak pressure with the inlet held open against the trip setting', 'fig07_fs3_trip_peak', 'run27_n5';
'Figure 6.12', 'Receiver pressure over 40 strides with Option B at 20 and 27 kPa(g), and the pump state', 'fig13_receiver_40_strides', 'run27_n7';
'Figure M.2',  'Peak device torque against alpha in the two windows', 'rpt', 'rpt_fig_M2';
'Figure M.3',  'Pressure needed at the peak against alpha over the hinge-depth band', 'rpt', 'rpt_fig_M3';
'Figure M.4',  'Torque relation, re-plotted from the closed-form relations of Appendix J', 'rpt', 'rpt_fig_M4';
'Figure M.5',  'Fill at the slowest case (receiver 53 kPa(g), room temperature, one MHJ10)', 'fig04_fill_slowest_case', 'run27_n2_n3';
'Figure M.6',  'Controller board: sl_ka_logic -> ka_logic_step', 'fig16_simulink_controller', 'run27_simulink';
'Figure M.7',  'Valves: inlet = MIN of the 1.0 ms and 0.5 ms delayed commands', 'fig17_simulink_valves', 'run27_simulink';
'Figure M.8',  'Pneumatic plant: sl_ka_plant -> ka_plant_deriv', 'fig18_simulink_plant', 'run27_simulink';
'Figure M.9',  'Simulink against the script, 27 kPa side case', 'fig14_simulink_vs_script_P27_W2_in1', 'run27_simulink';
'Figure M.11', 'Bladder pressure after each fault, starting at the set point', 'fig06_n5_faults', 'run27_n5';
'Figure M.12', 'Window 1 (comparison): demand pulses at 59-310 ms', 'fig09_demand_pulses_w1', 'run27_n1_n4';
'Figure M.13', 'Torque x time before the onset and missing in the window against the clock error', 'fig12_timing_tolerance', 'run27_n6';
'Figure M.14', 'Knee angle of constraint B-C04 with the bladder pressure', 'fig10_knee_angle_pressure', 'run27_n1_n4'};
end

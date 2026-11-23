function mdl = build_ka_simulink(mdl)
%BUILD_KA_SIMULINK  Builds the Simulink model knee_assist_rev27.slx from blocks (Rev 27, Week 11).
%
%   Structure (same order of operations as ka_simulate.m):
%     Pressure sensor (Delay 1.0 ms)  ->  Controller board  ->  Valves  ->  Pneumatic plant
%       Controller board : Interpreted MATLAB Function sl_ka_logic -> ka_logic_step
%                          (contact rules G-1..G-5, window clock, PI + FF + AW (Rev 22),
%                           200 Hz PWM, faults, trip, watchdog, supply switch, pump switch)
%       Valves           : MHJ10 inlet  = min(Delay 1.0 ms, Delay 0.5 ms) of its command
%                          (design system: ONE MHJ10; the flow comes from ka_p.n_in)
%                          MHE3 exhaust = 1 - max(Delay 2.53 ms, Delay 3.08 ms) of its power
%                          (e1 = the correcting exhaust, e2 = the other n_exh - 1 as one group)
%       Pneumatic plant  : Interpreted MATLAB Function sl_ka_plant -> ka_plant_deriv
%                          (ISO 6358 valve + tube tables, bladder energy balance, receiver,
%                           pump) and three Integrators: bladder pressure P, air mass m,
%                           receiver pressure pr
%   Fixed-step ode1 (Euler) at ka_sl.dt = 10 us, like the script.
%   Uses only standard Simulink blocks; no compiler, no Stateflow.
%
%   Run it through sim_ka_simulink.m, which sets ka_p, ka_cfg and ka_sl first.

if nargin < 1, mdl = 'knee_assist_rev27'; end
here = fileparts(mfilename('fullpath'));
if bdIsLoaded(mdl), close_system(mdl, 0); end
f = fullfile(here, [mdl '.slx']);
if exist(f, 'file'), delete(f); end
new_system(mdl);
open_system(mdl);
set_param(mdl, 'SolverType', 'Fixed-step', 'Solver', 'ode1', 'FixedStep', 'ka_sl.dt', ...
          'StartTime', '0', 'StopTime', 'ka_sl.t_end', 'SaveTime', 'off', 'SaveOutput', 'off', ...
          'ReturnWorkspaceOutputs', 'on');
try set_param(mdl, 'EnableMultiTasking', 'off'); catch; end
try set_param(mdl, 'SolverMode', 'SingleTasking'); catch; end
% Callbacks: put the model's own folder on the path when it is opened (so the
% MATLAB functions are found from any current folder), and make the inputs only
% when the run starts and they are missing (design system: 20 kPa, window 2, one MHJ10, two MHE3).
% Nothing slow runs while the model opens.
addp = sprintf('addpath(fileparts(get_param(''%s'', ''FileName'')));', mdl);
set_param(mdl, 'PreLoadFcn', '');
set_param(mdl, 'PostLoadFcn', addp);
% 'clear sl_ka_logic sl_ka_plant' resets their memory at the start of every run.
set_param(mdl, 'InitFcn', [addp ' clear sl_ka_logic sl_ka_plant; if ~(exist(''ka_sl'',''var'') && exist(''ka_p'',''var'') && exist(''ka_cfg'',''var'')), ka_simulink_setup; end']);

%% ================= Controller board =================
cb = [mdl '/Controller board'];
make_subsystem(cb, [330 80 520 300]);
add_block('simulink/Sources/In1',  [cb '/pm'], 'Position', [30 60 60 74]);
add_block('simulink/Sources/In1',  [cb '/pr'], 'Position', [30 110 60 124]);
add_block('simulink/Sources/Clock', [cb '/Clock'], 'Position', [30 10 60 30]);
add_block('simulink/Signal Routing/Mux', [cb '/Mux'], 'Inputs', '3', 'Position', [110 10 115 130]);
add_block('simulink/User-Defined Functions/Interpreted MATLAB Function', [cb '/ka_logic_step'], ...
          'MATLABFcn', 'sl_ka_logic(u)', 'OutputDimensions', '8', 'SampleTime', 'ka_sl.dt', ...
          'Position', [160 50 300 90]);
add_block('simulink/Signal Routing/Demux', [cb '/Demux'], 'Outputs', '8', 'Position', [340 10 345 250]);
outs = {'in_cmd', 'e1_pow', 'e2_pow', 'pump', 'w', 'r', 'u', 'stage'};
for i = 1:8
    add_block('simulink/Sinks/Out1', [cb '/' outs{i}], 'Position', [400 5+30*i 430 19+30*i]);
end
add_line(cb, 'Clock/1', 'Mux/1');  add_line(cb, 'pm/1', 'Mux/2');  add_line(cb, 'pr/1', 'Mux/3');
add_line(cb, 'Mux/1', 'ka_logic_step/1');  add_line(cb, 'ka_logic_step/1', 'Demux/1');
for i = 1:8, add_line(cb, sprintf('Demux/%d', i), [outs{i} '/1']); end

%% ================= Valves =================
vb = [mdl '/Valves'];
make_subsystem(vb, [600 80 760 220]);
add_block('simulink/Sources/In1', [vb '/in_cmd'], 'Position', [20 40 50 54]);
add_block('simulink/Sources/In1', [vb '/e1_pow'], 'Position', [20 150 50 164]);
add_block('simulink/Sources/In1', [vb '/e2_pow'], 'Position', [20 260 50 274]);
% MHJ10 inlet (normally closed): opens 1.0 ms after the command, closes 0.5 ms after release
add_block('simulink/Discrete/Delay', [vb '/MHJ10 open 1.0 ms'], 'DelayLength', 'ka_sl.d_in_on', ...
          'InitialCondition', 'ka_sl.in0', 'SampleTime', 'ka_sl.dt', 'Position', [100 20 160 50]);
add_block('simulink/Discrete/Delay', [vb '/MHJ10 close 0.5 ms'], 'DelayLength', 'ka_sl.d_in_off', ...
          'InitialCondition', 'ka_sl.in0', 'SampleTime', 'ka_sl.dt', 'Position', [100 70 160 100]);
add_block('simulink/Math Operations/MinMax', [vb '/inlet open = min'], 'Function', 'min', 'Inputs', '2', ...
          'Position', [210 40 240 80]);
add_line(vb, 'in_cmd/1', 'MHJ10 open 1.0 ms/1');  add_line(vb, 'in_cmd/1', 'MHJ10 close 0.5 ms/1');
add_line(vb, 'MHJ10 open 1.0 ms/1', 'inlet open = min/1');  add_line(vb, 'MHJ10 close 0.5 ms/1', 'inlet open = min/2');
add_block('simulink/Sinks/Out1', [vb '/in_open'], 'Position', [380 53 410 67]);
add_line(vb, 'inlet open = min/1', 'in_open/1');
% MHE3 exhausts (normally open): shut 2.53 ms after power, open 3.08 ms after release;
% e1 = the correcting exhaust, e2 = the other n_exh - 1 exhausts as one group
for j = 1:2
    y0 = 130 + 110*(j-1);  nm = sprintf('e%d', j);
    add_block('simulink/Discrete/Delay', [vb '/MHE3 ' nm ' shut 2.53 ms'], 'DelayLength', 'ka_sl.d_ex_on', ...
              'InitialCondition', 'ka_sl.ex0', 'SampleTime', 'ka_sl.dt', 'Position', [100 y0 160 y0+30]);
    add_block('simulink/Discrete/Delay', [vb '/MHE3 ' nm ' open 3.08 ms'], 'DelayLength', 'ka_sl.d_ex_off', ...
              'InitialCondition', 'ka_sl.ex0', 'SampleTime', 'ka_sl.dt', 'Position', [100 y0+50 160 y0+80]);
    add_block('simulink/Math Operations/MinMax', [vb '/' nm ' powered = max'], 'Function', 'max', 'Inputs', '2', ...
              'Position', [210 y0+20 240 y0+60]);
    add_block('simulink/Sources/Constant', [vb '/one ' nm], 'Value', '1', 'Position', [210 y0-15 240 y0+5]);
    add_block('simulink/Math Operations/Sum', [vb '/' nm ' open = 1 - powered'], 'Inputs', '+-', ...
              'Position', [290 y0+10 320 y0+40]);
    add_block('simulink/Sinks/Out1', [vb '/' nm '_open'], 'Position', [380 y0+18 410 y0+32]);
    add_line(vb, [nm '_pow/1'], ['MHE3 ' nm ' shut 2.53 ms/1']);
    add_line(vb, [nm '_pow/1'], ['MHE3 ' nm ' open 3.08 ms/1']);
    add_line(vb, ['MHE3 ' nm ' shut 2.53 ms/1'], [nm ' powered = max/1']);
    add_line(vb, ['MHE3 ' nm ' open 3.08 ms/1'], [nm ' powered = max/2']);
    add_line(vb, ['one ' nm '/1'], [nm ' open = 1 - powered/1']);
    add_line(vb, [nm ' powered = max/1'], [nm ' open = 1 - powered/2']);
    add_line(vb, [nm ' open = 1 - powered/1'], [nm '_open/1']);
end

%% ================= Pneumatic plant =================
pb = [mdl '/Pneumatic plant'];
make_subsystem(pb, [840 80 1010 240]);
add_block('simulink/Sources/In1', [pb '/in_open'], 'Position', [20 120 50 134]);
add_block('simulink/Sources/In1', [pb '/e1_open'], 'Position', [20 160 50 174]);
add_block('simulink/Sources/In1', [pb '/e2_open'], 'Position', [20 200 50 214]);
add_block('simulink/Sources/In1', [pb '/pump'],    'Position', [20 240 50 254]);
add_block('simulink/Sources/Clock', [pb '/Clock'], 'Position', [20 10 50 30]);
add_block('simulink/Signal Routing/Mux', [pb '/Mux'], 'Inputs', '8', 'Position', [120 10 125 260]);
add_block('simulink/User-Defined Functions/Interpreted MATLAB Function', [pb '/ka_plant_deriv'], ...
          'MATLABFcn', 'sl_ka_plant(u)', 'OutputDimensions', '6', 'SampleTime', '0', ...
          'Position', [170 115 310 155]);
add_block('simulink/Signal Routing/Demux', [pb '/Demux'], 'Outputs', '6', 'Position', [350 60 355 210]);
add_block('simulink/Continuous/Integrator', [pb '/P bladder (Pa)'], 'InitialCondition', 'ka_sl.P0', ...
          'Position', [420 300 460 330]);
add_block('simulink/Continuous/Integrator', [pb '/m air (kg)'], 'InitialCondition', 'ka_sl.m0', ...
          'Position', [420 350 460 380]);
add_block('simulink/Continuous/Integrator', [pb '/pr receiver (kPa g)'], 'InitialCondition', 'ka_sl.pr0', ...
          'Position', [420 400 460 430]);
add_line(pb, 'Clock/1', 'Mux/1');
add_line(pb, 'P bladder (Pa)/1', 'Mux/2', 'autorouting', 'on');
add_line(pb, 'm air (kg)/1', 'Mux/3', 'autorouting', 'on');
add_line(pb, 'pr receiver (kPa g)/1', 'Mux/4', 'autorouting', 'on');
add_line(pb, 'in_open/1', 'Mux/5');  add_line(pb, 'e1_open/1', 'Mux/6');
add_line(pb, 'e2_open/1', 'Mux/7');  add_line(pb, 'pump/1', 'Mux/8');
add_line(pb, 'Mux/1', 'ka_plant_deriv/1');  add_line(pb, 'ka_plant_deriv/1', 'Demux/1');
add_line(pb, 'Demux/1', 'P bladder (Pa)/1', 'autorouting', 'on');
add_line(pb, 'Demux/2', 'm air (kg)/1', 'autorouting', 'on');
add_line(pb, 'Demux/3', 'pr receiver (kPa g)/1', 'autorouting', 'on');
po = {'p_g', 4; 'T', 5; 'mdot_in', 6};
for i = 1:3
    add_block('simulink/Sinks/Out1', [pb '/' po{i,1}], 'Position', [520 40+50*i 550 54+50*i]);
    add_line(pb, sprintf('Demux/%d', po{i,2}), [po{i,1} '/1']);
end
add_block('simulink/Sinks/Out1', [pb '/pr'], 'Position', [520 408 550 422]);
add_line(pb, 'pr receiver (kPa g)/1', 'pr/1');

%% ================= sensor, wiring, logging =================
add_block('simulink/Discrete/Delay', [mdl '/Pressure sensor 1.0 ms'], 'DelayLength', 'ka_sl.d_sen', ...
          'InitialCondition', 'ka_sl.p0', 'SampleTime', 'ka_sl.dt', 'Position', [150 90 230 130]);
add_line(mdl, 'Pneumatic plant/1', 'Pressure sensor 1.0 ms/1', 'autorouting', 'on');
add_line(mdl, 'Pressure sensor 1.0 ms/1', 'Controller board/1', 'autorouting', 'on');
add_line(mdl, 'Pneumatic plant/4', 'Controller board/2', 'autorouting', 'on');
add_line(mdl, 'Controller board/1', 'Valves/1');
add_line(mdl, 'Controller board/2', 'Valves/2');
add_line(mdl, 'Controller board/3', 'Valves/3');
add_line(mdl, 'Valves/1', 'Pneumatic plant/1');
add_line(mdl, 'Valves/2', 'Pneumatic plant/2');
add_line(mdl, 'Valves/3', 'Pneumatic plant/3');
add_line(mdl, 'Controller board/4', 'Pneumatic plant/4', 'autorouting', 'on');

logs = {'sl_p',     'Pneumatic plant/1', [1100 60];
        'sl_T',     'Pneumatic plant/2', [1100 110];
        'sl_mdin',  'Pneumatic plant/3', [1100 160];
        'sl_pr',    'Pneumatic plant/4', [1100 210];
        'sl_inopen','Valves/1',          [1100 260];
        'sl_e1open','Valves/2',          [1100 310];
        'sl_w',     'Controller board/5',[1100 360];
        'sl_r',     'Controller board/6',[1100 410];
        'sl_u',     'Controller board/7',[1100 460];
        'sl_stage', 'Controller board/8',[1100 510];
        'sl_pm',    'Pressure sensor 1.0 ms/1', [1100 560]};
for i = 1:size(logs, 1)
    pos = logs{i,3};
    add_block('simulink/Sinks/To Workspace', [mdl '/' logs{i,1}], 'VariableName', logs{i,1}, ...
              'SaveFormat', 'Array', 'MaxDataPoints', 'inf', 'Decimation', 'ka_sl.decim', ...
              'Position', [pos(1) pos(2) pos(1)+80 pos(2)+25]);
    add_line(mdl, logs{i,2}, [logs{i,1} '/1'], 'autorouting', 'on');
end
add_block('simulink/Sources/Clock', [mdl '/Clock'], 'Position', [1000 620 1030 640]);
add_block('simulink/Sinks/To Workspace', [mdl '/sl_t'], 'VariableName', 'sl_t', 'SaveFormat', 'Array', ...
          'MaxDataPoints', 'inf', 'Decimation', 'ka_sl.decim', 'Position', [1100 610 1180 635]);
add_line(mdl, 'Clock/1', 'sl_t/1');
add_block('simulink/Signal Routing/Mux', [mdl '/Scope mux'], 'Inputs', '2', 'Position', [1000 680 1005 730]);
add_block('simulink/Sinks/Scope', [mdl '/Bladder and reference (kPa g)'], 'Position', [1060 685 1100 725]);
add_line(mdl, 'Pneumatic plant/1', 'Scope mux/1', 'autorouting', 'on');
add_line(mdl, 'Controller board/6', 'Scope mux/2', 'autorouting', 'on');
add_line(mdl, 'Scope mux/1', 'Bladder and reference (kPa g)/1');

try
    add_block('built-in/Note', [mdl '/Knee assist Rev 27 (Week 11) - pneumatic loop, actuator-V8 (391 mL), k3D 0.207 N m per kPa. Design system: 20 kPa, window 2 (13-36 %), ONE MHJ10, two MHE3 at the port; relief valve = future work. Hardware PROPOSED, NOT APPROVED (ka_params.m).'], ...
              'Position', [150 20]);
catch
end

save_system(mdl, f);
fprintf('Built %s\n', f);
end

function make_subsystem(path, pos)
add_block('simulink/Ports & Subsystems/Subsystem', path, 'Position', pos);
try
    delete_line(path, 'In1/1', 'Out1/1');
catch
end
try delete_block([path '/In1']); catch; end
try delete_block([path '/Out1']); catch; end
end

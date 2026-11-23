%RUN_ALL_REV27  Runs the whole Rev 27 model and writes results\rev27_results.csv.
%
%   Order: inputs -> N2/N3 -> N5 -> N1/N4 -> N6 -> N7 -> Simulink check.
%   Figures go to results\ (PNG and FIG). Each value is printed with the hand
%   calculation next to it where one exists (Appendix J of the final report).
%   Hardware values: see ka_params.m.
%   The pressure-relief valve is not fitted and is not in any run.
here = fileparts(mfilename('fullpath'));
addpath(here);
if ~exist(fullfile(here, 'results'), 'dir'), mkdir(fullfile(here, 'results')); end
set(0, 'DefaultFigureVisible', 'off');
ka_report('reset');
csv = fullfile(here, 'results', 'rev27_results.csv');
t_all = tic;
p0 = ka_setup(1, 1, 2, 'timing', false);
ka_print_hardware(p0);
fprintf('B3: %s\nB4: %s\nPatient moment: %s\n', p0.b3_source, p0.b4_source, p0.pm_source);
parts = {};
try, Rin = run27_inputs(true);  close all;  parts{end+1} = 'inputs';           catch e, fprintf(2, 'inputs failed: %s\n', getReport(e)); end
ka_report('save', csv);
try, R23 = run27_n2_n3(true);   close all;  parts{end+1} = 'N2/N3';            catch e, fprintf(2, 'N2/N3 failed: %s\n', getReport(e)); end
ka_report('save', csv);
try, R5 = run27_n5(true);       close all;  parts{end+1} = 'N5';               catch e, fprintf(2, 'N5 failed: %s\n', getReport(e)); end
ka_report('save', csv);
try, R14 = run27_n1_n4(true);   close all;  parts{end+1} = 'N1/N4';            catch e, fprintf(2, 'N1/N4 failed: %s\n', getReport(e)); end
ka_report('save', csv);
save(fullfile(here, 'results', 'rev27_params.mat'), 'R14', '-v7.3');
try, R6 = run27_n6(R14.p, true); close all; parts{end+1} = 'N6';               catch e, fprintf(2, 'N6 failed: %s\n', getReport(e)); end
ka_report('save', csv);
try, R7 = run27_n7(R14.p, true); close all; parts{end+1} = 'N7';               catch e, fprintf(2, 'N7 failed: %s\n', getReport(e)); end
ka_report('save', csv);
try, RS = run27_simulink(R14.p); close all; parts{end+1} = 'Simulink';         catch e, fprintf(2, 'Simulink failed: %s\n', getReport(e)); end
T = ka_report('save', csv);
fprintf('\nDone in %.1f min: %s. %d values written to results\\rev27_results.csv\n', toc(t_all)/60, strjoin(parts, ', '), height(T));
h = ~isnan(T.hand);
fprintf('%d values have a hand calculation; largest differences:\n', nnz(h));
[~, ix] = sort(abs(T.diff_pct(h)), 'descend');  hi = find(h);
for i = hi(ix(1:min(15, numel(ix))))'
    fprintf('  %-26s %-60s model %9.4g  hand %9.4g  (%+.2f %%)\n', T.id{i}, T.item{i}, T.model(i), T.hand(i), T.diff_pct(i));
end

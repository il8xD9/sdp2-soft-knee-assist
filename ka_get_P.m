function P = ka_get_P()
%KA_GET_P  Parameter set P = R.p from run27_n1_n4, for run27_n6 / run27_n7 / run27_simulink
%   when they are called without an input (e.g. typing "run27_n6" at the prompt).
%   1) loads results\rev27_params.mat (saved by run_all_rev27) if it is there;
%   2) otherwise runs run27_n1_n4(false) (no figures, several minutes) and saves it.
here = fileparts(mfilename('fullpath'));
f = fullfile(here, 'results', 'rev27_params.mat');
if exist(f, 'file')
    S = load(f, 'R14');
    if isfield(S, 'R14') && isfield(S.R14, 'p') && ~isempty(S.R14.p)
        P = S.R14.p;
        fprintf('Using P from %s\n', f);
        return
    end
end
fprintf('No saved parameters found: running run27_n1_n4 first (no figures)...\n');
R14 = run27_n1_n4(false);
P = R14.p;
if ~exist(fullfile(here, 'results'), 'dir'), mkdir(fullfile(here, 'results')); end
save(f, 'R14', '-v7.3');
end

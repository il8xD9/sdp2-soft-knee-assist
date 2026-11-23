function p = ka_setup(pcase, n_in, window, varargin)
%KA_SETUP  Ready-to-run parameters: ka_params -> changes -> ka_prepare -> fill timing.
%   p = ka_setup                          DESIGN SYSTEM: 20 kPa, one MHJ10, window option 2
%   p = ka_setup(pc, n_in, window)        pc 1 = 20 kPa, 2 = 27 kPa; n_in MHJ10; window 1 or 2
%   p = ka_setup(pc, n_in, window, 'V_mult', 1.5, ...)   any ka_params field changed
%                                         before the tables are built
%   Options: 'timing', false   skip the G-5 floor / fill-command search (fault runs)
%            'exh_b', b        re-derive the exhaust C for another b
%            'dt', 20e-6       time step (pulse runs)
if nargin < 1 || isempty(pcase),  pcase = 1;  end
if nargin < 2 || isempty(n_in),   n_in = 1;   end
if nargin < 3 || isempty(window), window = 2; end
if mod(numel(varargin), 2) ~= 0
    error('ka_setup: changes must come in name / value pairs');
end
p = ka_params(pcase, n_in, window);
do_timing = true;
for i = 1:2:numel(varargin)
    if strcmp(varargin{i}, 'timing')
        do_timing = varargin{i+1};
    elseif strcmp(varargin{i}, 'exh_b')
        p = ka_exhaust_from_qn(p, 200, varargin{i+1});
    elseif isfield(p, varargin{i})
        p.(varargin{i}) = varargin{i+1};
    else
        error('ka_setup: unknown parameter %s', varargin{i});
    end
end
p = ka_prepare(p);
if do_timing
    [p.fill_floor, p.t_fill_demand] = ka_fill_timing(p);
end
end

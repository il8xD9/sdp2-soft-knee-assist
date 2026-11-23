function ka_simulink_setup(p, cfg)
%KA_SIMULINK_SETUP  Puts ka_p, ka_cfg and ka_sl in the base workspace for the Simulink model.
%   ka_simulink_setup              DESIGN SYSTEM (Rev 27): 20 kPa, window 2, one MHJ10,
%                                  demand pulse, two MHE3 at the port, one stride
%   ka_simulink_setup(p, cfg)      any p from ka_setup and cfg (same as for ka_simulate)
%   The model calls this itself (InitFcn) when ka_sl is missing.
if nargin < 1 || isempty(p)
    p = ka_setup(1, 1, 2);
end
if nargin < 2 || isempty(cfg)
    cfg = ka_default_cfg('pulse', 'demand', 'n_exh', p.n_exh_sys, 'exh_at_port', true, 'pr_kPa', 53, 't_end', 0.66);
end
if ~isfield(p, 'in_tab')
    error('ka_simulink_setup: p has no flow tables; make it with ka_setup (or ka_params + ka_prepare)');
end
if cfg.n_exh < 1 || cfg.n_exh > p.ex_nmax
    error('ka_simulink_setup: n_exh must be 1..%d', p.ex_nmax);
end
if strcmp(cfg.init, 'filling')
    warning('ka_simulink_setup:init', ['init = ''filling'': the Simulink sensor Delay starts at p0, while ' ...
            'ka_simulate starts it on a falling ramp; fault runs belong in ka_simulate.']);
end
dt = p.dt;
s.dt     = dt;
if isnan(cfg.t_end), s.t_end = cfg.n_strides * p.T_stride; else, s.t_end = cfg.t_end; end
s.t_end  = s.t_end - dt;                       % same number of steps as ka_simulate
s.d_in_on  = round(p.in_t_open / dt);   s.d_in_off = round(p.in_t_close / dt);
s.d_ex_on  = round(p.exh_t_close / dt); s.d_ex_off = round(p.exh_t_open / dt);
s.d_sen    = round(p.sens_delay / dt);
s.in0 = double(strcmp(cfg.init, 'filling'));
s.ex0 = double(any(strcmp(cfg.init, {'filling', 'holding'})));
s.p0  = cfg.p0_kPa;
s.P0  = cfg.p0_kPa * 1e3 + p.p_atm;
s.m0  = s.P0 * p.V / (p.R * p.T0);
s.pr0 = cfg.pr_kPa;
s.decim = cfg.log_every;
s.option = p.option;  s.window = p.window;  s.n_in = p.n_in;
assignin('base', 'ka_p', p);
assignin('base', 'ka_cfg', cfg);
assignin('base', 'ka_sl', s);
fprintf('Simulink inputs set: %s, %s, %d MHJ10, %s pulse, %d MHE3\n', p.opt_name, p.win_name, p.n_in, cfg.pulse, cfg.n_exh);
end

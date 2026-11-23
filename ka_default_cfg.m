function cfg = ka_default_cfg(varargin)
%KA_DEFAULT_CFG  Run settings for ka_simulate, with name/value overrides.
%   cfg = ka_default_cfg('pulse','demand','adiabatic',true,'pr_kPa',70)
cfg.pulse            = 'bounding';  % 'bounding' | 'demand' | 'none'
cfg.adiabatic        = false;       % heat case: false = room temperature, true = no heat exchange
cfg.pr_kPa           = 53;          % receiver, kPa(g) (start value if dynamic)
cfg.receiver_dynamic = false;       % true: receiver drawn down and refilled by the pump
cfg.n_exh            = 1;           % installed MHE3 exhausts: 1 = close-out basis, 2 = complete
                                    % system, 5 = v7 swing squeeze (exhaust 1 makes the corrections)
cfg.exh_at_port      = false;       % false: exhaust behind the tube; true: at the bladder port
cfg.n_strides        = 1;
cfg.t_end            = NaN;         % s; NaN = n_strides x stride
cfg.clock_err        = 0;           % s, window clock error, negative = early
cfg.contact          = 'ideal';     % 'ideal' (clock error given) | 'sensor' (footswitches + G rules)
cfg.stance           = NaN;         % s, true stance (NaN = 0.705 s)
cfg.contacts         = [];          % N x 2 [t_start t_end] true contacts (s) for 'sensor'
cfg.sample_phase     = 0;           % s, first footswitch sample
cfg.insole_delay     = NaN;         % s, insole delay for 'sensor' (NaN = p.insole_delay)
cfg.abort_rule       = true;        % G-2
cfg.abort_w          = NaN;         % s on the window clock: forced G-2 abort (false-contact runs)
cfg.fill_at          = NaN;         % s on the window clock, overrides the fill rule
cfg.fault            = 'none';      % 'power_loss' | 'frozen_hold' | 'inlet_open' | 'stuck_all'
cfg.t_fault          = 0;           % s
cfg.p0_kPa           = 0;           % start pressure, kPa(g)
cfg.init             = 'vented';    % 'vented' | 'filling' (inlet open) | 'holding' (all shut)
cfg.watchdog         = false;
cfg.trip_kPa         = NaN;         % NaN = no trip
cfg.trip_err_kPa     = 0;           % trip sensor reads low by this
cfg.log_every        = 1;
cfg.stop_vented      = false;       % true: end the run early once the 24 V supply is off, the inlet is
                                    % shut, every exhaust is open and the bladder is at or below 2.4 kPa(g):
                                    % from then on the pressure can only fall, so the vent time and the
                                    % peak are unchanged (fault runs; about 3 times faster)
for i = 1:2:numel(varargin)
    if ~isfield(cfg, varargin{i})
        error('ka_default_cfg: unknown setting %s', varargin{i});
    end
    cfg.(varargin{i}) = varargin{i+1};
end
end

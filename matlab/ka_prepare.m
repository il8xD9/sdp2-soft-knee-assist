function p = ka_prepare(p)
%KA_PREPARE  Derived values, valve flow tables, gait waveforms and the
%   fastest-fill reference. Call again after changing any hardware, tube or
%   volume value (or p.n_in); after changing only the option, ka_derived(p)
%   is enough.
%
%   Tables (ISO 6358 valve in series with the 80 mm tube, solved once):
%     p.in_tab(i,j)  inlet path mass flow (kg/s) of all p.n_in MHJ10 together,
%                    receiver p_r = (i-1)*in_dr kPa(g), bladder p_b = (j-1)*in_db kPa(g)
%     p.ex_tab(j,c)  exhaust path mass flow (kg/s) at bladder (j-1)*ex_dp kPa(g);
%                    c = n            : n MHE3 through the tube   (n = 1..ex_nmax)
%                    c = n + ex_nmax  : n MHE3 at the bladder port

p.in_C = p.n_in * p.in_C_one;                     % MHJ10 in parallel
p.V = (p.V_cav + p.V_tube) * p.V_mult;

% ---- exhaust tables ----
p.ex_dp = 0.05;                                   % kPa
gb = (0 : p.ex_dp : 300)';
pb = gb * 1e3 + p.p_atm;
p.ex_tab = zeros(numel(gb), 2 * p.ex_nmax);
for at_port = 0:1
    for n = 1:p.ex_nmax
        p.ex_tab(:, n + p.ex_nmax*at_port) = ka_series_flow('exhaust', pb, p.p_atm, n, at_port, p);
    end
end
p.ex_n = numel(gb);

% ---- inlet table ----
p.in_dr = 1.0;  p.in_db = 0.1;                    % kPa
gr = 0 : p.in_dr : 250;
gb = 0 : p.in_db : 250;
[PR, PB] = ndgrid(gr * 1e3 + p.p_atm, gb * 1e3 + p.p_atm);
p.in_tab = ka_series_flow('inlet', PR, PB, 1, 0, p);
p.in_nr = numel(gr);  p.in_nb = numel(gb);

% ---- B3 demand shape and B4 knee angle ----
p = ka_gait_data(p);

% ---- option-dependent values ----
p = ka_derived(p);

% ---- fastest fill: no heat exchange, receiver 70 kPa(g) ----
[p.ff_t, p.ff_p] = ka_open_fill(p, 70, true, 60, 0.6);
p.ff_rate_p = 0 : 0.1 : 69.9;                     % kPa(g)
p.ff_rate = zeros(size(p.ff_rate_p));             % kPa/s
for i = 1:numel(p.ff_rate_p)
    p.ff_rate(i) = p.gam * p.R * p.T0 / p.V * ka_lookup_in(p, 70, p.ff_rate_p(i)) / 1e3;
end
end

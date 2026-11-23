function d = ka_deficit(p, t, T_stance)
%KA_DEFICIT  B1 full deficit tau_full (N m) at time t (s) after contact,
%   inside the active window (p.win_on_pct .. p.win_off_pct), 0 outside.
%   Interpolated linearly on the 0.1 % grid of ka_gait_data.
%   T_stance (optional) scales the window for the stance-time check (N6).
if nargin < 3, T_stance = p.T_stance; end
s = t / T_stance * 100;
d = zeros(size(t));
in = s >= p.win_on_pct & s <= p.win_off_pct;
if any(in(:))
    d(in) = interp1(p.b3_pct, p.b3_def, s(in), 'linear', 'extrap');
end
end

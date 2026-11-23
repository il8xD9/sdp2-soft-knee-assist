function p = ka_derived(p)
%KA_DERIVED  Values that follow from the pressure case, the window and the torque relation.
%   k      torque per kPa (N m/kPa):
%          '3D' (governing): k3D = dV/dtheta on the CAD cavity
%               = 206 990 mm^3 at d_h 65 mm -> 0.2070 N m/kPa (hand calculation SH-C04);
%               other d_h from the k3D band (0/50/65/80 mm), linear between them
%          '2D' (comparison): k2D = A_i (d_h + 28 mm) = 198 707 mm^3 -> 0.1987 N m/kPa
%   alpha  design alpha: deficit peak (33 N m) x alpha just reaches the set point
%          -> 0.1255 / 0.1694 (20 / 27 kPa) with k3D
%   p_on   onset demand = tau_req(onset) / k, capped at the set point:
%          window 1: alpha x 7.056 N m / k  (21.4 % of the set point)
%          window 2: MIN(alpha x 19.43, 1.424) N m / k = 6.88 kPa (patient's moment caps it)
p.V = (p.V_cav + p.V_tube) * p.V_mult;
switch p.k_basis
    case '3D'
        dh_mm = p.d_h * 1e3;
        p.k_m3 = interp1(p.k3D_band(1,:), p.k3D_band(2,:), dh_mm, 'linear', 'extrap') * 1e-9;
        if abs(dh_mm - 65) < 1e-9, p.k_m3 = p.k3D; end
    case '2D'
        p.k_m3 = p.A_i * (p.d_h + p.d_off);
    otherwise
        error('ka_derived: k_basis must be ''3D'' or ''2D''');
end
p.k_Nm_per_kPa = p.k_m3 * 1e3;                         % N m per kPa
p.alpha        = p.cap_kPa * p.k_Nm_per_kPa / p.def_peak;
p.t_on         = p.win_on_pct  / 100 * p.T_stance;
p.t_off        = p.win_off_pct / 100 * p.T_stance;
p.t_deadline   = p.deadline_pct / 100 * p.T_stance;
if isfield(p, 'b3_pct')
    p.p_on_kPa = min(ka_torque_req(p, p.t_on) / p.k_Nm_per_kPa, p.cap_kPa);
    p.tq_on    = ka_torque_req(p, p.t_on);
    p.tq_off   = ka_torque_req(p, p.t_off);
else
    p.p_on_kPa = NaN;  p.tq_on = NaN;  p.tq_off = NaN;   % set by ka_prepare after ka_gait_data
end
end

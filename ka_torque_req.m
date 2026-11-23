function tq = ka_torque_req(p, t, T_stance)
%KA_TORQUE_REQ  Torque the controller is asked to give (N m) at time t (s) after contact.
%   Window option 1: tau_req = alpha x tau_full(t)                      (8.43-44 % stance)
%   Window option 2: tau_req = MIN(alpha x tau_full(t), M_patient(t))   (13-36 % stance)
%   0 outside the window. The set-point cap (k x p_sp) is applied by the caller.
%   T_stance (optional) scales the window for the stance-time check (N6).
if nargin < 3, T_stance = p.T_stance; end
tq = p.alpha * ka_deficit(p, t, T_stance);
if p.cap_patient
    s = t / T_stance * 100;
    in = s >= p.win_on_pct & s <= p.win_off_pct;
    if any(in(:))
        mp = interp1(p.pm_pct, p.pm_Nm, s(in), 'linear', 'extrap');
        tq(in) = min(tq(in), max(mp, 0));
    end
end
end

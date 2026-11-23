function pb = ka_stuck_open(p, pr_kPa, n_exh, at_port)
%KA_STUCK_OPEN  Steady bladder pressure (kPa(g)) with the inlet stuck open
%   mechanically and the exhausts open, receiver at pr_kPa, room temperature.
%   at_port = true : inlet -> tube -> bladder -> n MHE3 at the port
%   at_port = false: inlet and MHE3 share the manifold node; the bladder sits
%                    behind the tube with no net flow, so it equals the node
pr = pr_kPa * 1e3 + p.p_atm;
lo = p.p_atm;  hi = pr;
for it = 1:80
    mid = 0.5 * (lo + hi);
    if at_port
        q_in  = ka_series_flow('inlet', pr, mid, 1, 0, p);
        q_out = ka_series_flow('exhaust', mid, p.p_atm, n_exh, 1, p);
    else
        q_in  = ka_iso6358(p.in_C, p.in_b, pr, mid, p.rho_anr);
        q_out = ka_iso6358(n_exh * p.exh_C * p.exh_C_mult, p.exh_b, mid, p.p_atm, p.rho_anr);
    end
    if q_in > q_out, lo = mid; else, hi = mid; end
end
pb = (0.5 * (lo + hi) - p.p_atm) / 1e3;
end

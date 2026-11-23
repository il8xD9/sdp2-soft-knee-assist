function md = ka_series_flow(path, pu, pd, n, at_port, p)
%KA_SERIES_FLOW  Mass flow (kg/s) of a valve in series with the tube, T = T0.
%   'inlet'  : receiver pu -> MHJ10 -> node -> tube -> bladder pd
%   'exhaust': bladder pu -> tube -> node -> n x MHE3 -> atmosphere pd
%              (at_port = 1: valves at the bladder port, no tube)
%   Solved by bisection on the mass flow (vectorised over pu, pd).
rho0 = p.rho_anr;
switch path
    case 'inlet'
        md0 = ka_iso6358(p.in_C, p.in_b, pu, pd, rho0);
        md0(pu <= pd) = 0;
        if ~p.tube_on
            md = md0;  return
        end
        rho = pd / (p.R * p.T0);
        lo = zeros(size(md0));  hi = md0;
        for it = 1:60
            mid = 0.5 * (lo + hi);
            pn  = pd + ka_tube_dp(mid, rho, p);            % node pressure before the tube
            mv  = ka_iso6358(p.in_C, p.in_b, pu, min(pn, pu), rho0);
            mv(~(pu > pn)) = 0;
            up  = mv > mid;
            lo(up) = mid(up);  hi(~up) = mid(~up);
        end
        md = 0.5 * (lo + hi);
    case 'exhaust'
        C = n * p.exh_C * p.exh_C_mult;
        pdv = pd * ones(size(pu));
        md0 = ka_iso6358(C, p.exh_b, pu, pdv, rho0);
        if at_port || ~p.tube_on
            md = md0;  return
        end
        rho = pu / (p.R * p.T0);
        lo = zeros(size(md0));  hi = md0;
        for it = 1:60
            mid = 0.5 * (lo + hi);
            pn  = pu - ka_tube_dp(mid, rho, p);            % node pressure at the valves
            mv  = ka_iso6358(C, p.exh_b, max(pn, pd), pdv, rho0);
            mv(~(pn > pd)) = 0;
            up  = mv > mid;
            lo(up) = mid(up);  hi(~up) = mid(~up);
        end
        md = 0.5 * (lo + hi);
    otherwise
        error('ka_series_flow: unknown path %s', path);
end
end

function [t, pg] = ka_open_fill(p, pr_kPa, adiabatic, p_stop_kPa, t_max)
%KA_OPEN_FILL  Open-loop fill: inlet commanded at t = 0 (opens after
%   p.in_t_open), exhausts shut, receiver fixed at pr_kPa (kPa(g)).
%   Returns time (s) and bladder pressure (kPa(g)) until p_stop_kPa or t_max.
%   Used for the fastest-fill reference (adiabatic, 70 kPa(g)) and for the
%   fill timing of PR-15 (room temperature, 53 kPa(g), the slowest case).
dt = p.dt;  R = p.R;  T0 = p.T0;  V = p.V;
P = p.p_atm;
n = round(t_max / dt);
pg = zeros(n + 1, 1);
k_open = round(p.in_t_open / dt);
for k = 0:n-1
    g = (P - p.p_atm) / 1e3;
    pg(k+1) = g;
    if g >= p_stop_kPa
        pg = pg(1:k+1);  t = (0:k)' * dt;
        return
    end
    md = 0;
    if k >= k_open
        md = ka_lookup_in(p, pr_kPa, g);
    end
    if adiabatic
        P = P + p.gam * R * T0 / V * md * dt;     % inflow only: dP/dt = gam R T0 mdot / V
    else
        P = P + R * T0 / V * md * dt;
    end
end
pg(n+1) = (P - p.p_atm) / 1e3;
t = (0:n)' * dt;
end

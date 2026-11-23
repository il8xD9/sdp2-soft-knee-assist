function [dP, dm, dpr, md_in, md_out, T] = ka_plant_deriv(P, m, pr, in_open, n_open, pump, p, adiabatic, rec_dyn, at_port, rel_open)
%KA_PLANT_DERIV  Pneumatic plant: valve flows, bladder energy balance, receiver.
%   P      bladder absolute pressure (Pa)       m   air mass in the bladder (kg)
%   pr     receiver pressure, kPa(g)
%   in_open  inlet(s) actually open (after their delays); all p.n_in MHJ10 together
%   n_open   number of MHE3 exhausts actually open (0 .. p.ex_nmax)
%   pump     pump running
%   adiabatic  true: no heat exchange (gas temperature follows the energy
%              balance); false: room temperature (isothermal)
%   rec_dyn    true: receiver pressure changes (pump and draw); false: fixed
%   at_port    exhausts at the bladder port (true) or behind the tube (false)
%   rel_open   relief valve open (Circle Seal L500, screening only; hysteresis kept by the caller)
%
%   Bladder (rigid volume V, Xavier 2022 Eq. 4 with n = 1 or gamma):
%     no heat exchange: dP/dt = gam R / V (T0 mdot_in - T mdot_out),  T = P V / (m R)
%     room temperature: dP/dt = R T0 / V (mdot_in - mdot_out)
%   Receiver (room temperature): dpr/dt = R T0 / Vr (mdot_pump - mdot_in)
%   Pump: free-air flow on the straight line between its two data-sheet points.
if nargin < 11, rel_open = false; end
R = p.R;  T0 = p.T0;  V = p.V;
pg = (P - p.p_atm) / 1e3;
if adiabatic
    T = P * V / (m * R);
else
    T = T0;
end
md_in = 0;
if in_open
    md_in = ka_lookup_in(p, pr, pg);
end
md_out = 0;
if n_open > 0
    md_out = ka_lookup_ex(p, n_open + p.ex_nmax * at_port, pg) * sqrt(T0 / T);
end
if rel_open
    md_out = md_out + ka_relief_flow(p, pg) * sqrt(T0 / T);
end
if adiabatic
    dP = p.gam * R / V * (T0 * md_in - T * md_out);
else
    dP = R * T0 / V * (md_in - md_out);
end
dm = md_in - md_out;
dpr = 0;
if rec_dyn
    md_p = 0;
    if pump
        md_p = p.rho_anr * p.pump_Qfree * max(1 - pr / p.pump_pmax_kPa, 0);
    end
    dpr = R * T0 / p.Vr * (md_p - md_in) / 1e3;
end
end

function p = ka_exhaust_from_qn(p, q_nl_min, b)
%KA_EXHAUST_FROM_QN  Exhaust C from a Festo standard nominal flow and a chosen b.
%   q_nl_min  standard nominal flow, normal litres/min (DIN 1343: 0 C, 1.01325 bar),
%             measured at 6 bar(g) inlet and 1 bar drop
%   b         critical pressure ratio (Festo gives none for MHE3; 0 = slowest case)
%   Converts normal litres to ANR litres (ISO 6358 / ISO 8778: 20 C, 100 kPa).
p1 = 6e5 + p.p_atm;  p2 = 5e5 + p.p_atm;
rho_n = 101325 / (p.R * 273.15);
q_anr = q_nl_min / 60e3 * rho_n / p.rho_anr;
r = p2 / p1;
if r <= b
    psi = 1;
else
    psi = sqrt(1 - ((r - b) / (1 - b))^2);
end
p.exh_b = b;
p.exh_C = q_anr / (p1 * psi);
end

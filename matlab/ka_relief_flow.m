function md = ka_relief_flow(p, pg_kPa)
%KA_RELIEF_FLOW  Mass flow (kg/s) of the open Circle Seal L500 relief valve at the
%   bladder pressure pg_kPa (kPa(g)). Data-sheet flow (SCFM at 14.7 psia, 60 F)
%   at 0 / 10 / 25 / 50 % over the 3.2 psig cracking pressure, linear between the
%   points and extended linearly above the last one (Rev 24e Section 11.9).
pp = p.rel_p_kPa;  q = p.rel_q_scfm * 0.47194745e-3;     % m^3/s standard
if pg_kPa <= pp(1)
    md = 0;  return
end
if pg_kPa >= pp(end)
    qs = q(end) + (pg_kPa - pp(end)) * (q(end) - q(end-1)) / (pp(end) - pp(end-1));
else
    qs = interp1(pp, q, pg_kPa);
end
md = qs * 101325 / (p.R * 288.71);                       % standard density (60 F)
end

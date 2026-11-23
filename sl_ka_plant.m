function y = sl_ka_plant(u)
%SL_KA_PLANT  Simulink wrapper of ka_plant_deriv (Interpreted MATLAB Function block).
%   u = [t; P; m; pr; in_open; e1_open; e2_open; pump]
%   y = [dP/dt; dm/dt; dpr/dt; p_g (kPa(g)); T (K); mdot_in (kg/s)]
%   ka_p and ka_cfg are read from the base workspace at t = 0 of each run.
%   e2_open stands for the other cfg.n_exh - 1 exhausts (one group); the relief
%   valve (p.relief_on) keeps its open / shut state here, with the same hysteresis
%   as ka_simulate.
persistent p cfg rel_open
if isempty(p) || u(1) <= 0
    p   = evalin('base', 'ka_p');
    cfg = evalin('base', 'ka_cfg');
    rel_open = false;
end
in_open = u(5) > 0.5;
n_open  = double(u(6) > 0.5) + double(u(7) > 0.5) * (cfg.n_exh - 1);
pg = (u(2) - p.p_atm) / 1e3;
if p.relief_on
    if ~rel_open && pg >= p.rel_crack_kPa
        rel_open = true;
    elseif rel_open && pg <= p.rel_reseat_kPa
        rel_open = false;
    end
end
[dP, dm, dpr, md_in, ~, T] = ka_plant_deriv(u(2), u(3), u(4), in_open, n_open, u(8) > 0.5, ...
                                            p, cfg.adiabatic, cfg.receiver_dynamic, cfg.exh_at_port, rel_open);
y = [dP; dm; dpr; pg; T; md_in];
end

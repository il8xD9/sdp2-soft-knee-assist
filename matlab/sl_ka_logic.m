function y = sl_ka_logic(u)
%SL_KA_LOGIC  Simulink wrapper of ka_logic_step (Interpreted MATLAB Function block).
%   u = [t; pm; pr]   time (s), controller sensor reading (kPa(g)), receiver (kPa(g))
%   y = [in_cmd; e1_pow; e2_pow; pump; w; r; u; stage]
%   Reads ka_p and ka_cfg from the base workspace at the first step of each run
%   (set by sim_ka_simulink.m). A repeated call at the same step returns the
%   stored output, so the controller memory advances exactly once per step.
persistent last_k last_y dt
t = u(1);
if isempty(last_k) || (t <= 0 && last_k ~= 0)
    p   = evalin('base', 'ka_p');
    cfg = evalin('base', 'ka_cfg');
    dt  = p.dt;
    ka_logic_step('init', p, cfg);
    last_k = -1;  last_y = zeros(8, 1);
end
k = round(t / dt);
if k == last_k
    y = last_y;  return
end
[in_cmd, e1_pow, e2_pow, pump, w, dg] = ka_logic_step('step', k, u(2), u(3));
y = [double(in_cmd); double(e1_pow); double(e2_pow); double(pump); w; dg(1); dg(2); dg(3)];
last_k = k;  last_y = y;
end

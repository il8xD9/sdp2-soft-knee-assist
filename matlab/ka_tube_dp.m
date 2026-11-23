function dp = ka_tube_dp(md, rho, p)
%KA_TUBE_DP  Pressure drop (Pa) of the 4 mm x 80 mm tube for mass flow md (kg/s).
%   Darcy friction from Churchill (1977), smooth wall, all flow regimes,
%   plus entrance 0.5 + exit 1.0 (Cengel & Cimbala Table 8-4).
A  = pi/4 * p.tube_D^2;
Re = max(md * p.tube_D ./ (A * p.mu), 1e-9);
a  = (2.457 * log(1 ./ ((7 ./ Re).^0.9))).^16;
bb = (37530 ./ Re).^16;
f  = 8 * ((8 ./ Re).^12 + 1 ./ (a + bb).^1.5).^(1/12);
v  = md ./ (rho * A);
dp = (f * p.tube_L / p.tube_D + p.tube_K) .* rho .* v.^2 / 2;
end

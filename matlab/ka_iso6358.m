function md = ka_iso6358(C, b, pu, pd, rho0)
%KA_ISO6358  Mass flow through a valve, ISO 6358-1 (Xavier 2022 Eq. 7).
%   C    sonic conductance, m^3/(s Pa) (1 l/(s bar) = 1e-8)
%   b    critical pressure ratio
%   pu   upstream absolute pressure (Pa), pd downstream (Pa); arrays allowed
%   rho0 ANR density (kg/m^3). Upstream temperature = T0 (scale by sqrt(T0/T) outside).
r   = pd ./ pu;
x   = min(max((r - b) ./ (1 - b), 0), 1);
psi = sqrt(max(1 - x.^2, 0));
psi(r <= b) = 1;
psi(r >= 1) = 0;
md  = C .* rho0 .* pu .* psi;
end

function md = ka_lookup_ex(p, col, pg_kPa)
%KA_LOOKUP_EX  Exhaust path mass flow (kg/s) at T0, linear in p.ex_tab(:,col).
%   col = n_open + p.ex_nmax*at_port, pg_kPa bladder kPa(g).
%   Use ka_excol(p, n, at_port) to get the column.
if pg_kPa <= 0
    md = 0;  return
end
x = pg_kPa / p.ex_dp;
i = floor(x);
if i >= p.ex_n - 1
    md = p.ex_tab(end, col);  return
end
f = x - i;
md = p.ex_tab(i+1, col) + f * (p.ex_tab(i+2, col) - p.ex_tab(i+1, col));
end

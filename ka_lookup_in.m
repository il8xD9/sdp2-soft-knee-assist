function md = ka_lookup_in(p, pr_kPa, pb_kPa)
%KA_LOOKUP_IN  Inlet path mass flow (kg/s), bilinear in p.in_tab.
%   pr_kPa receiver, pb_kPa bladder, both kPa(g). One-way valve.
if pb_kPa >= pr_kPa
    md = 0;  return
end
if pb_kPa < 0, pb_kPa = 0; end
x = pr_kPa / p.in_dr;  y = pb_kPa / p.in_db;
i = min(floor(x), p.in_nr - 2);  j = min(floor(y), p.in_nb - 2);
fx = x - i;  fy = y - j;
t = p.in_tab;
md = (1-fx) * ((1-fy) * t(i+1, j+1) + fy * t(i+1, j+2)) + ...
        fx  * ((1-fy) * t(i+2, j+1) + fy * t(i+2, j+2));
end

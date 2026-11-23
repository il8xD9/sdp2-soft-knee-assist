function c = ka_excol(p, n, at_port)
%KA_EXCOL  Column of p.ex_tab for n MHE3 exhausts, through the tube (at_port = false)
%   or at the bladder port (at_port = true).
c = n + p.ex_nmax * double(logical(at_port));
end

function p = rpt_base(pcase, window)
%RPT_BASE  Parameters for the analytical report figures (no flow tables, no fill timing).
%   p = rpt_base             design point 20 kPa(g), window option 2, one MHJ10
%   p = rpt_base(pc, w)      pc 1 = 20 kPa, 2 = 27 kPa; w 1 or 2
%   Uses ka_params -> ka_gait_data (Basem's curves from data\) -> ka_derived (k3D, alpha).
%   This takes well under a second; the simulation runs use ka_setup instead.
if nargin < 1 || isempty(pcase),  pcase = 1;  end
if nargin < 2 || isempty(window), window = 2; end
p = ka_params(pcase, 1, window);
p = ka_gait_data(p);
p = ka_derived(p);
end

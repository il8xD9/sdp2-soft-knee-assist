function p = ka_set_option(p, pcase)
%KA_SET_OPTION  Set point and trip of each pressure case (Rev 27, PROPOSED levels).
%   1: design point, Basem O1 v10 B7 row 6: 20 kPa   set point 20, trip 22.6 kPa(g)
%   2: side case,    Basem O1 v10 B7 row 7: 27 kPa   set point 27, trip 29.6 kPa(g)
%      (individual calibration only; replaces the 28 kPa of B7 v8 used up to Rev 25a, CF-01)
%   The controller holds the bladder at the limit on its own sensor (Rev 22).
%   trip = set point + 2 x 1.25 (two sensor errors) + 0.1 (control allowance)
%   p.cap_kPa is the set point (kept under its Rev 21 name for the code).
lim  = [20 27];
names = {'Design point 20 kPa', 'Side case 27 kPa'};
p.option    = pcase;
p.opt_name  = names{pcase};
p.opt_short = sprintf('P%d', lim(pcase));
p.limit_kPa = lim(pcase);
p.cap_kPa   = lim(pcase);
p.trip_kPa  = lim(pcase) + 2 * p.sens_err_kPa + p.ctrl_allow_kPa;
end

function p = ka_set_window(p, window)
%KA_SET_WINDOW  Assistance window (Basem O1 v10 B3 / O2 v3 B3_Opt2, Rev 27).
%   2: window option 2 (MAIN, decision D-2): 13-36 % stance = 91.65-253.8 ms;
%      tau_req = MIN(alpha x tau_full, patient's own moment)
%   1: window option 1 (comparison): 8.43-44 % stance = 59.4-310.2 ms;
%      tau_req = alpha x tau_full
%   After a change call ka_derived(p) (onset demand, window times).
p.window = window;
if window == 2
    p.win_on_pct  = 13.0;
    p.win_off_pct = 36.0;
    p.cap_patient = true;
    p.win_name    = 'Window 2 (13-36 %)';
    p.win_short   = 'W2';
else
    p.win_on_pct  = 8.43;
    p.win_off_pct = 44.0;
    p.cap_patient = false;
    p.win_name    = 'Window 1 (8.43-44 %)';
    p.win_short   = 'W1';
end
end

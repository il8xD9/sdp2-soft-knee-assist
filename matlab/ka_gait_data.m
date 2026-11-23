function p = ka_gait_data(p)
%KA_GAIT_DATA  Deficit (B1/B3), patient moment (B3 option 2) and knee angle (B4).
%
%   The curves of the biomechanics model are read from data\:
%     data\B3_deficit.csv              stance_pct, deficit_Nm   (tau_full, alpha = 1)
%     data\B3_patient_moment_opt2.csv  stance_pct, patient_moment_Nm (13-36 %, window 2 cap)
%     data\B4_knee_angle.csv           stance_pct, knee_deg      (0-100 % stance)
%   The deficit and the knee angle are joined by pchip on a 0.1 % grid; the
%   patient moment is linear between the 1 % stance frames (ka_torque_req).
%   If a file is missing, a built-in approximation of the curve is used.

here = fileparts(mfilename('fullpath'));
f3 = fullfile(here, 'data', 'B3_deficit.csv');
f3p = fullfile(here, 'data', 'B3_patient_moment_opt2.csv');
f4 = fullfile(here, 'data', 'B4_knee_angle.csv');
on1 = 8.43;  off1 = 44.0;          % widest window (option 1): the deficit is defined over it

%% ---- B1/B3 deficit ----
if exist(f3, 'file')
    M = read_csv(f3);
    s = unique([on1, 8.5:0.1:44, off1, M(:,1)']);
    s = s(s >= on1 & s <= off1);
    p.b3_pct = s;
    p.b3_def = pchip(M(:,1)', M(:,2)', s);
    p.b3_pts = M;
    p.b3_source = 'Biomechanics model (data\B3_deficit.csv)';
else
    s = unique([0:1:100, on1, off1]);
    d = zeros(size(s));
    pk = p.def_peak_pct;  def_on = 7.06;  def_off = 6.20;
    a_b = 1.5;  b_b = 2.17;
    rise = s >= on1 & s <= pk;   x = (s(rise) - on1) / (pk - on1);
    d(rise) = def_on + (p.def_peak - def_on) * betainc(x, a_b, b_b);
    rel = s > pk & s <= off1;    x = (s(rel) - pk) / (off1 - pk);
    d(rel) = def_off + (p.def_peak - def_off) * 0.5 * (1 + cos(pi * x));
    p.b3_pct = s;  p.b3_def = d;  p.b3_pts = [];
    p.b3_source = 'DERIVED approximation (data file missing)';
end

%% ---- patient's own moment (window option 2 cap) ----
if exist(f3p, 'file')
    M = read_csv(f3p);
    p.pm_pct = M(:,1)';  p.pm_Nm = M(:,2)';
    p.pm_source = 'Biomechanics model (data\B3_patient_moment_opt2.csv)';
else
    p.pm_pct = [13 36];  p.pm_Nm = [1e3 1e3];       % no cap
    p.pm_source = 'none (no cap)';
end

%% ---- B4 knee angle over the stride ----
if exist(f4, 'file')
    M = read_csv(f4);
    kt = [M(:,1)' / 100 * p.T_stance, 0.846, p.T_stride];
    ky = [M(:,2)', 65, M(1,2)];
    p.b4_pts = M;
    p.b4_source = 'Biomechanics model (data\B4_knee_angle.csv) + healthy swing 65 deg';
else
    kt = [0, 42, 59.43, 148.05, 310.2, 420, 613.35, 705, 846, 1175] / 1e3;
    ky = [-1.92, 0, 0.9, 5.8, 0.7, 0.5, 10.4, 27.8, 65, -1.92];
    p.b4_pts = [];
    p.b4_source = 'DERIVED approximation (data file missing)';
end
p.b4_t   = (0:1175) / 1e3;
p.b4_deg = pchip(kt, ky, p.b4_t);
end

function M = read_csv(f)
try
    M = readmatrix(f);
catch
    M = csvread(f, 1, 0); %#ok<CSVRD>
end
M = M(all(isfinite(M), 2), :);
end

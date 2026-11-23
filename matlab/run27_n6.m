function R = run27_n6(P, make_figs)
%RUN27_N6  N6 assistance at the wrong time (trigger faults), Rev 27.
%   P = R.p from run27_n1_n4 (parameters with their fill timing).
%   Window 2 (main), 20 / 27 kPa, one MHJ10 (system) and two MHJ10 (comparison);
%   complete system (two MHE3 at the port); worst of the four heat / receiver cases.
%   Figure 12 (timing tolerance).
if nargin < 1 || isempty(P), P = ka_get_P(); end   % allows running with no input
if nargin < 2, make_figs = true; end
fprintf('\n===== N6 trigger faults =====\n');
t0 = tic;
cases = [0 53; 0 70; 1 53; 1 70];
spec = {'pulse','demand','n_exh',2,'exh_at_port',true,'t_end',0.40};
R = struct();

%% ---- timing tolerance (0.5 ms grid) ----
for nin = 1:2
    for pc = 1:2
        p = P{nin, pc, 2};  o = sprintf('%s.W2.in%d', p.opt_short, nin);  nm = sprintf('W2, %s, %d MHJ10', p.opt_name, nin);
        early = side(@(e) worst_of(p, cases, spec, e), -1);
        late  = side(@(e) worst_of(p, cases, spec, e), +1);
        ka_report('add', ['N6.early.' o], [nm ': clock may be early by (NaN = fails at 0)'], early, NaN, 'ms');
        ka_report('add', ['N6.late.' o],  [nm ': clock may be late by'], late, NaN, 'ms');
        [b, mm] = worst_err(p, cases, spec, -0.004);
        ka_report('add', ['N6.m4b.' o], [nm ': clock -4 ms, before the onset'], b, NaN, '%');
        ka_report('add', ['N6.m4m.' o], [nm ': clock -4 ms, missing'], mm, NaN, '%');
        [b, mm] = worst_err(p, cases, spec, 0.004);
        ka_report('add', ['N6.p4b.' o], [nm ': clock +4 ms, before the onset'], b, NaN, '%');
        ka_report('add', ['N6.p4m.' o], [nm ': clock +4 ms, missing'], mm, NaN, '%');
        if nin == 1
            ge = (-24:2:20) / 1e3;  B = zeros(size(ge));  Mi = B;
            for j = 1:numel(ge), [B(j), Mi(j)] = worst_err(p, cases, spec, ge(j)); end
            R.grid_e = ge;  R.before{pc} = B;  R.missing{pc} = Mi;
        end
        fprintf('  %s [%.0f s]\n', nm, toc(t0));
    end
end

%% ---- stance time: fixed schedule against true stances 0.58-0.80 s ----
st = 0.58:0.02:0.80;
for pc = 1:2
    p = P{1, pc, 2};  o = p.opt_short;
    Bs = zeros(size(st));  Ms = Bs;
    for j = 1:numel(st)
        for i = 1:size(cases, 1)
            c = ka_default_cfg('adiabatic', logical(cases(i,1)), 'pr_kPa', cases(i,2), spec{:}, 't_end', max(0.40, 0.6 * st(j)));
            m = ka_metrics_demand(p, ka_simulate(p, c), st(j));
            Bs(j) = max(Bs(j), m.before_pct);  Ms(j) = max(Ms(j), m.missing_pct);
        end
    end
    ok = Bs <= 10 & Ms <= 10;
    R.st = st;  R.stB{pc} = Bs;  R.stM{pc} = Ms;
    lo = st(find(ok, 1, 'first'));  hi = st(find(ok, 1, 'last'));
    if isempty(lo), lo = NaN; hi = NaN; end
    ka_report('add', ['N6.st.lo.' o], sprintf('W2, %s, one MHJ10: shortest valid stance (0.02 s grid)', p.opt_name), lo, NaN, 's');
    ka_report('add', ['N6.st.hi.' o], sprintf('W2, %s, one MHJ10: longest valid stance (0.02 s grid)', p.opt_name), hi, NaN, 's');
end
fprintf('  stance done [%.0f s]\n', toc(t0));

%% ---- false contacts (forced G-2 abort at 5.6 + D + 9.6 ms on the window clock) ----
D = [20 40 60 80 100];
for pc = 1:2
    p = P{1, pc, 2};  o = [p.opt_short '.W2.in1'];
    for j = 1:numel(D)
        pk = 0;  ab = 0;
        for i = 1:size(cases, 1)
            c = ka_default_cfg('adiabatic', logical(cases(i,1)), 'pr_kPa', cases(i,2), spec{:}, 't_end', 0.5, ...
                               'abort_w', (5.6 + D(j) + 9.6) / 1e3);
            r = ka_simulate(p, c);
            pk = max(pk, max(r.log.p));  ab = max(ab, sum(r.log.p > p.rest_kPa) * p.dt * 1e3);
        end
        ka_report('add', sprintf('N6.fc%d.pk.%s', D(j), o), sprintf('W2, %s: false contact %d ms, peak', p.opt_name, D(j)), pk, NaN, 'kPa');
        ka_report('add', sprintf('N6.fc%d.ab.%s', D(j), o), sprintf('W2, %s: false contact %d ms, time above 2.4 kPa', p.opt_name, D(j)), ab, NaN, 'ms');
    end
    st_ = p.exh_t_close - p.in_t_open;
    ka_report('add', ['N6.noair.' o], sprintf('W2, %s: longest false contact that lets no air in', p.opt_name), ...
              (p.t_fill_demand + st_ + p.in_t_open) * 1e3 - 15.2, NaN, 'ms');
end

%% ---- footswitch scenarios (1 kHz sensor model and the contact rules) ----
T = 1.175;  S = 0.705;
sc = {'normal',   'Normal walking',                     [0 S; T T+S], true;
      'missed',   'Missed contact (stride 1)',          [T T+S], true;
      'stuckoff', 'Sensor stuck off',                   [10 11], true;
      'stuckon',  'Sensor stuck on',                    [0 100], true;
      'bounce',   'Bounce at heel strike (3 ms gap)',   [0 0.004; 0.007 S; T T+S], true;
      'false20',  'False contact in swing, 20 ms',      [0 S; 0.905 0.925; T T+S], true;
      'noabort',  'False contact 20 ms, no abort rule', [0 S; 0.905 0.925; T T+S], false};
for pc = 1:2
    p = P{1, pc, 2};  o = p.opt_short;
    for s = 1:size(sc, 1)
        c = ka_default_cfg('pulse','demand','n_exh',2,'exh_at_port',true,'contact','sensor', ...
                           'contacts', sc{s,3}, 'abort_rule', sc{s,4}, 'pr_kPa', 53, 't_end', 2*T);
        r = ka_simulate(p, c);
        w = r.log.t >= S & r.log.t < T;  if any(strcmp(sc{s,1}, {'missed','stuckoff'})), w = r.log.t < T; end
        ka_report('add', sprintf('N6.%s.pk.%s', sc{s,1}, o), sprintf('W2, %s, %s: highest pressure outside stance 1', p.opt_name, sc{s,2}), max(r.log.p(w)), NaN, 'kPa');
        ka_report('add', sprintf('N6.%s.np.%s', sc{s,1}, o), sprintf('W2, %s, %s: pulses started in 2 strides', p.opt_name, sc{s,2}), numel(r.ev.enable), NaN, '-');
    end
end
fprintf('  footswitch scenarios done [%.0f s]\n', toc(t0));

%% ---- figure ----
if make_figs
    C = ka_colours();
    figure('Name', 'Timing tolerance', 'Color', 'w', 'Position', [60 60 1000 420]);  hold on;  grid on;
    patch([-4 4 4 -4], [0 0 40 40], [0.9 0.95 1], 'EdgeColor', 'none', 'HandleVisibility', 'off');
    col = {C.s1, C.s2};  nm = {'20 kPa', '27 kPa'};
    for pc = 1:2
        plot(R.grid_e*1e3, R.before{pc},  '-',  'Color', col{pc}, 'LineWidth', 1.6, 'DisplayName', sprintf('%s: before the onset', nm{pc}));
        plot(R.grid_e*1e3, R.missing{pc}, '--', 'Color', col{pc}, 'LineWidth', 1.6, 'DisplayName', sprintf('%s: missing in the window', nm{pc}));
    end
    yline(10, ':k', '10 % level', 'HandleVisibility', 'off');
    xlabel('window clock error (ms), negative = early');  ylabel('% of the torque x time asked');
    ylim([0 40]);  legend('Location', 'north');
    title('Timing tolerance, window 2, one MHJ10, two MHE3 (shaded: \pm4 ms footswitches)');
    ka_savefig('fig12_timing_tolerance');
end
fprintf('N6 done in %.1f min\n', toc(t0) / 60);
end

%% =====================================================================
function [b, mm] = worst_err(p, cases, spec, e)
b = 0;  mm = 0;
for i = 1:size(cases, 1)
    c = ka_default_cfg('adiabatic', logical(cases(i,1)), 'pr_kPa', cases(i,2), 'clock_err', e, spec{:});
    m = ka_metrics_demand(p, ka_simulate(p, c));
    b = max(b, m.before_pct);  mm = max(mm, m.missing_pct);
end
end
function v = worst_of(p, cases, spec, e)
[b, mm] = worst_err(p, cases, spec, e);
v = max(b, mm);
end
function x = side(f, sgn)
if f(0) > 10, x = NaN; return, end
ok = 0;
for e = 2:2:40
    if f(sgn * e / 1e3) > 10, break, end
    ok = e;
end
for e = ok + 0.5 : 0.5 : ok + 1.5
    if f(sgn * e / 1e3) > 10, break, end
    ok = e;
end
x = ok;
end

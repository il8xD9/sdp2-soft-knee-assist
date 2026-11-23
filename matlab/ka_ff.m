function out = ka_ff(p, what, x)
%KA_FF  Fastest-fill reference (no heat exchange, receiver 70 kPa(g)).
%   ka_ff(p,'value',tau)   pressure (kPa(g)) tau s after the inlet command
%   ka_ff(p,'time',level)  time (s) from the inlet command to reach level (kPa(g))
%   ka_ff(p,'rate',pg)     fastest fill rate (kPa/s) at bladder pg (kPa(g))
switch what
    case 'value'
        if x <= 0
            out = 0;
        else
            out = interp1q_lin(p.ff_t, p.ff_p, x);
        end
    case 'time'
        i = find(p.ff_p >= x, 1, 'first');
        if isempty(i)
            out = p.ff_t(end);
        elseif i == 1
            out = 0;
        else
            out = p.ff_t(i-1) + (x - p.ff_p(i-1)) / (p.ff_p(i) - p.ff_p(i-1)) * (p.ff_t(i) - p.ff_t(i-1));
        end
    case 'rate'
        out = interp1q_lin(p.ff_rate_p(:), p.ff_rate(:), x);
    otherwise
        error('ka_ff: unknown request %s', what);
end
end

function y = interp1q_lin(xv, yv, x)
% linear interpolation on a uniform grid, clamped at the ends
if x <= xv(1),  y = yv(1);  return, end
if x >= xv(end), y = yv(end); return, end
h = xv(2) - xv(1);
i = floor((x - xv(1)) / h) + 1;
i = min(max(i, 1), numel(xv) - 1);
y = yv(i) + (x - xv(i)) / (xv(i+1) - xv(i)) * (yv(i+1) - yv(i));
end

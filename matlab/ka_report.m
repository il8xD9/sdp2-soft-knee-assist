function out = ka_report(cmd, varargin)
%KA_REPORT  Collects Rev 27 model values next to the hand-calculation value (if any).
%   ka_report('reset')
%   ka_report('add', id, item, model_value, hand_value, unit)
%        hand_value NaN = no hand calculation for this value (model only)
%   T = ka_report('table')               all rows as a table
%   ka_report('save', file)              CSV: id, item, model, hand, diff, diff_pct, unit
%   The hand values are those of Nawaf_Rev27_Hand_Calculations (Week 11) and of
%   Meshal & Nawaf hand calc v5, where a hand check exists.
persistent R
if isempty(R), R = cell(0, 5); end
out = [];
switch cmd
    case 'reset'
        R = cell(0, 5);
    case 'add'
        v = varargin{3};
        if isempty(v) || ~isscalar(v), v = NaN; end
        R(end+1, :) = {varargin{1}, varargin{2}, double(v), double(varargin{4}), varargin{5}};
        d = varargin{4};
        if isnan(d)
            fprintf('  %-26s %-66s %10.4g %-8s\n', varargin{1}, varargin{2}, v, varargin{5});
        else
            fprintf('  %-26s %-66s %10.4g %-8s (hand: %g)\n', varargin{1}, varargin{2}, v, varargin{5}, d);
        end
    case 'table'
        out = make_table(R);
    case 'save'
        T = make_table(R);
        writetable(T, varargin{1});
        out = T;
end
end

function T = make_table(R)
id = R(:,1);  item = R(:,2);  model = cell2mat(R(:,3));  hand = cell2mat(R(:,4));  unit = R(:,5);
diff = model - hand;
diff_pct = diff ./ max(abs(hand), 1e-9) * 100;
diff_pct(isnan(hand)) = NaN;
T = table(id, item, model, hand, diff, diff_pct, unit);
end

function f = rpt_savefig(name, fig)
%RPT_SAVEFIG  Save a figure as results\report_figures\<name>.png (and .fig).
%   rpt_savefig('Figure_4_8')          current figure
%   rpt_savefig('Figure_4_8', h)       figure handle h
%   Returns the full path of the PNG.
if nargin < 2 || isempty(fig), fig = gcf; end
d = rpt_folder();
set(fig, 'PaperPositionMode', 'auto');
set(findall(fig, '-property', 'FontName'), 'FontName', 'Arial');
f = fullfile(d, [name '.png']);
print(fig, f, '-dpng', '-r150');
savefig(fig, fullfile(d, [name '.fig']));
end

function ka_savefig(name)
%KA_SAVEFIG  Save the current figure as results\<name>.png (and .fig).
here = fileparts(mfilename('fullpath'));
d = fullfile(here, 'results');
if ~exist(d, 'dir'), mkdir(d); end
set(gcf, 'PaperPositionMode', 'auto');
set(findall(gcf, '-property', 'FontName'), 'FontName', 'Arial');
print(gcf, fullfile(d, [name '.png']), '-dpng', '-r150');
savefig(gcf, fullfile(d, [name '.fig']));
end

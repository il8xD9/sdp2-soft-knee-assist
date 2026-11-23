function d = rpt_folder()
%RPT_FOLDER  Folder of the report figures: results\report_figures (made if missing).
here = fileparts(mfilename('fullpath'));
d = fullfile(here, 'results', 'report_figures');
if ~exist(d, 'dir'), mkdir(d); end
end

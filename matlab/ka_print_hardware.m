function ka_print_hardware(p)
%KA_PRINT_HARDWARE  Lists the hardware placeholders the model uses (NOT APPROVED).
fprintf('\nHARDWARE: %s\n', p.hw_status);
for i = 1:size(p.hw, 1)
    fprintf('  %-17s %s\n', p.hw{i,1}, p.hw{i,2});
    fprintf('  %-17s %s\n', '', p.hw{i,3});
    fprintf('  %-17s source: %s\n', '', p.hw{i,4});
end
fprintf('  Change the values in ka_params.m, then ka_prepare again.\n\n');
end

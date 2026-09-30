SELECT conrelid::regclass AS table_name,
       conname,
       contype,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY 1, 2;
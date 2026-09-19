SELECT
    i.id,
    i.match_id,
    m.opponent,
    m.venue,
    i.file_name,
    i.file_type
FROM public.sportscode_imports i
JOIN public.matches m
    ON m.id = i.match_id
WHERE m.opponent = 'Levski'
ORDER BY
    i.match_id,
    i.file_type,
    i.file_name;
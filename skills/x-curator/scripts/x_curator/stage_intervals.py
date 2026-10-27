"""Union of overlapping local processing intervals."""
_LOCAL = {'wiki.source_audit', 'wiki.page_render', 'wiki.site_render', 'wiki.link_validation',
          'wiki.file_validation', 'wiki.file_write', 'wiki.final_files', 'source.publication',
          'wiki.mapping_validation'}

def union_seconds(rows):
    intervals = sorted((row['monotonic_start'], row['monotonic_start'] + row['elapsed'])
                       for row in rows if row['stage'] in _LOCAL and row['elapsed'] is not None)
    if not intervals:
        return 0.0
    first, last = intervals[0]
    total = 0.0
    for start, end in intervals[1:]:
        if start > last:
            total += last - first
            first, last = start, end
        else:
            last = max(last, end)
    return total + last - first

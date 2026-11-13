"""RTM lookup for the cascade impact assessment.  Builder work (Claude), not independent.
usage: python3 -I rtm.py <RTM csv> <section> <heading number> [more heading numbers...]
Prints every RTM row of that section from the heading whose number is given (for example 14, or 12.8 for sections 12 and 13's
numbering, or 00.10) up to the next heading of the same level, with its paragraph index and the start of its text."""
import csv, re, sys

def rows(path):
    out = []
    for x in csv.DictReader(open(path, encoding='utf-8-sig')):
        m = re.search(r'paragraph_index=(\d+);(?: style=([^;]+);)? text_prefix=(.*)', x['source_anchor'], re.S)
        x['pi'] = int(m.group(1)) if m else -1
        x['style'] = (m.group(2) or '') if m else ''
        x['prefix'] = m.group(3) if m else x['source_anchor']
        out.append(x)
    return out

def heading_num(x):
    m = re.match(r'\s*([0-9]+(?:\.[0-9]+)*)\.?\s', x['prefix'])
    return m.group(1) if m else None

def level(x):
    if x['style'].startswith('Title'):
        return 1
    m = re.match(r'Heading (\d)', x['style'])
    return int(m.group(1)) if m else None

def span(all_rows, section, num):
    """the rows from heading `num` (any heading level) up to the next heading of the same or a higher level"""
    sec = sorted([x for x in all_rows if x['source_section'] == section], key=lambda x: x['pi'])
    for i, h in enumerate(sec):
        if level(h) and heading_num(h) == num:
            lv = level(h)
            end = next((y['pi'] for y in sec[i + 1:] if level(y) and level(y) <= lv), 10 ** 9)
            return [x for x in sec if h['pi'] <= x['pi'] < end]
    sys.exit('heading %s not found in section %s' % (num, section))

if __name__ == '__main__':
    R = rows(sys.argv[1])
    for num in sys.argv[3:]:
        for x in span(R, sys.argv[2], num):
            print('%s\tp%d\t%s' % (x['requirement_id'], x['pi'], x['requirement_summary'][:200].replace('\n', ' ')))
        print()

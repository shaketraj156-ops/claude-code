"""Deterministic, auditable prioritisation of recorded water measurements."""
from datetime import date
from briefs import make_brief, make_site_brief, FESTIVAL_ORDER

CORE = ('pH', 'Dissolved oxygen', 'BOD')
PHASES = ('pre', 'during', 'after')
METHOD_VERSION = '1.1'


def assessed(row):
    return bool(row and row['status'] in ('Within reference', 'Outside reference'))


def event_analysis(site, year, festival, readings):
    lookup = {(r['parameter'], r['phase']): r for r in readings}
    valid = [r for r in readings if assessed(r)]
    recovery = []
    for parameter in CORE:
        pre, during, after = [lookup.get((parameter, phase)) for phase in PHASES]
        if not assessed(after):
            status = 'After reading unavailable'
        elif after['severity'] > 0:
            status = 'Still outside reference' if assessed(during) and during['severity'] > 0 else 'Outside reference after immersion'
        elif assessed(during) and during['severity'] > 0:
            status = 'Returned within reference'
        elif assessed(during):
            status = 'Within reference during and after'
        else:
            status = 'After within reference; during unavailable'
        recovery.append({
            'parameter': parameter, 'status': status,
            'pre_id': pre['id'] if pre else None,
            'during_id': during['id'] if during else None,
            'after_id': after['id'] if after else None,
            'before_after_delta': after['value'] - pre['value'] if assessed(pre) and assessed(after) else None,
            'persistent': bool(assessed(during) and assessed(after) and during['severity'] > 0 and after['severity'] > 0),
        })
    return {
        'site': site, 'year': year, 'festival': festival,
        'row_ids': [r['id'] for r in readings], 'assessed': len(valid), 'expected': 9,
        'breaches': sum(r['severity'] > 0 for r in valid), 'absent': not readings,
        'before_after_pairs': sum(r['before_after_delta'] is not None for r in recovery),
        'recovery': recovery,
    }


def assign_ranks(groups, key, rank_field, eligible=lambda g: True):
    ordered = sorted(groups, key=lambda g: (*key(g), g['site'].casefold()))
    previous, rank, count = None, None, 0
    for group in ordered:
        if not eligible(group):
            group[rank_field] = None
            continue
        count += 1
        score = key(group)
        if score != previous:
            rank = count
        group[rank_field] = rank
        previous = score
    return [g['site'] for g in ordered]


def build_model(rows, limits):
    """Keep an observed site roster even when a site's entire event is missing."""
    sites = sorted({r['site'] for r in rows})
    years = sorted({r['year'] for r in rows})
    festivals = sorted({r['festival'] for r in rows}, key=lambda f: (FESTIVAL_ORDER.get(f, 9), f))
    event_keys = sorted({(r['year'], r['festival']) for r in rows}, key=lambda e: (e[0], FESTIVAL_ORDER.get(e[1], 9), e[1]))
    indexed = {}
    for row in rows:
        indexed.setdefault((row['site'], row['year'], row['festival']), []).append(row)
    histories = {site: [event_analysis(site, year, festival, indexed.get((site, year, festival), []))
                        for year, festival in event_keys] for site in sites}
    metadata = {}
    for site in sites:
        site_rows = [r for r in rows if r['site'] == site]
        metadata[site] = {
            'site_hi': next((r['site_hi'] for r in site_rows if r.get('site_hi')), ''),
            'water_body': next((r['water_body'] for r in site_rows if r.get('water_body')), 'Not supplied'),
            'identity_uncertain': any(r.get('site_match_confidence') == 'medium' for r in site_rows),
        }
    views = {}
    for year in ['all', *years]:
        for festival in ['all', *festivals]:
            scope = [(y, f) for y, f in event_keys if (year == 'all' or y == year) and (festival == 'all' or f == festival)]
            if not scope:
                continue
            groups = []
            for site in sites:
                events = [e for e in histories[site] if (e['year'], e['festival']) in scope]
                selected = [r for y, f in scope for r in indexed.get((site, y, f), [])]
                valid = [r for r in selected if assessed(r)]
                bad = [r for r in valid if r['severity'] > 0]
                worst = max(bad, key=lambda r: (r['severity'], r['year']), default=None)
                oxygen = [r for r in valid if r['parameter'] == 'Dissolved oxygen']
                oxygen_breaches = [r for r in oxygen if r['severity'] > 0]
                lowest_oxygen = min(oxygen, key=lambda r: (r['value'], -r['year']), default=None)
                oxygen_first = bool(oxygen_breaches)
                tier = 0 if oxygen_first else 1 if bad else 2 if valid else 3
                after = [r for r in valid if r['phase'] == 'after']
                latest = max((r['year'] for r in rows if r['site'] == site and assessed(r)
                              and (festival == 'all' or r['festival'] == festival)
                              and (year == 'all' or r['year'] <= year)), default=None)
                expected = 9 * len(scope)
                g = {
                    'site': site, **metadata[site], 'events': events,
                    'assessed': len(valid), 'breaches': len(bad), 'expected': expected,
                    'missing': expected - len(valid), 'coverage': len(valid) / expected,
                    'breach_rate': len(bad) / len(valid) if valid else None,
                    'worst_severity': worst['severity'] if worst else 0,
                    'worst_reading': worst, 'after_assessed': len(after),
                    'priority_tier': tier,
                    'oxygen_assessed': len(oxygen), 'oxygen_breaches': len(oxygen_breaches),
                    'minimum_oxygen': lowest_oxygen['value'] if lowest_oxygen else None,
                    'priority_reading': lowest_oxygen if oxygen_first else worst,
                    'after_breaches': sum(r['severity'] > 0 for r in after),
                    'persistent_pairs': sum(check['persistent'] for e in events for check in e['recovery']),
                    'latest_year': latest, 'absent_events': sum(e['absent'] for e in events),
                    'matched_sources': sum(bool(r.get('report')) for r in selected),
                    'row_count': len(selected),
                }
                groups.append(g)
            pollution = assign_ranks(groups, lambda g: (
                g['priority_tier'],
                g['minimum_oxygen'] if g['priority_tier'] == 0 else 0,
                -round(g['oxygen_breaches'] / g['oxygen_assessed'], 12) if g['priority_tier'] == 0 else 0,
                -round(g['worst_severity'], 12),
                -round(g['breach_rate'] or 0, 12),
            ), 'pollution_rank', lambda g: g['assessed'] > 0)
            testing = assign_ranks(groups, lambda g: (
                round(g['coverage'], 12), g['latest_year'] or 0, -int(g['identity_uncertain']),
            ), 'testing_rank')
            view = {
                'limits': limits,
                'year': year, 'festival': festival, 'site_count': len(groups),
                'event_count': len(scope), 'assessed': sum(g['assessed'] for g in groups),
                'expected': sum(g['expected'] for g in groups), 'breaches': sum(g['breaches'] for g in groups),
                'sites': groups, 'pollution_order': pollution, 'testing_order': testing,
            }
            view['brief_en'] = make_brief(view)
            view['brief_hi'] = make_brief(view, 'hi')
            for g in groups:
                g['brief_en'] = make_site_brief(g, view)
                g['brief_hi'] = make_site_brief(g, view, 'hi')
            views[f'{year}|{festival}'] = view
    return {'version': METHOD_VERSION, 'generated_date': date.today().isoformat(),
            'years': years, 'festivals': festivals, 'histories': histories, 'views': views}

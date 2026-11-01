"""Static conceptual map from the public registry; no runtime transfers inferred."""
from html import escape

POSITIONS = {
    'sug': (650, 90), 'weber': (115, 285), 'schneider': (115, 515),
    'hoffmann': (365, 285), 'reinhardt': (650, 285), 'vogel': (955, 285),
    'mueller': (365, 515), 'fischer': (580, 515), 'johanna': (790, 515),
    'adler': (1090, 515), 'braun': (475, 750), 'hartmann': (680, 750),
    'krueger': (885, 750), 'richter': (1090, 705), 'bergmann': (1090, 835),
}
HANDOFFS = [
    ('fischer', 'reinhardt', 'research', 'Reproducible experiments'),
    ('johanna', 'reinhardt', 'research', 'Cited observations and coverage gaps'),
    ('reinhardt', 'braun', 'evaluation', 'Bounded trend mandate'),
    ('reinhardt', 'hartmann', 'evaluation', 'Bounded momentum mandate'),
    ('reinhardt', 'krueger', 'evaluation', 'Bounded mean-reversion mandate'),
    ('braun', 'schneider', 'review', 'Candidate evidence for independent review'),
    ('hartmann', 'schneider', 'review', 'Candidate evidence for independent review'),
    ('krueger', 'schneider', 'review', 'Candidate evidence for independent review'),
    ('schneider', 'weber', 'risk', 'Independent evidence; risk veto remains separate'),
    ('weber', 'reinhardt', 'risk', 'Risk constraints or veto; never an order'),
    ('mueller', 'hoffmann', 'engineering', 'Measured resource costs and limits'),
    ('hoffmann', 'schneider', 'review', 'Repair and regression evidence'),
    ('schneider', 'sug', 'review', 'Independent acceptance or rejection'),
    ('hoffmann', 'sug', 'engineering', 'Validated engineering change proposal'),
    ('braun', 'vogel', 'reporting', 'Recorded strategy and reconciliation evidence'),
    ('hartmann', 'vogel', 'reporting', 'Recorded strategy and reconciliation evidence'),
    ('krueger', 'vogel', 'reporting', 'Recorded strategy and reconciliation evidence'),
    ('richter', 'adler', 'compliance', 'Securities and data-source questions'),
    ('bergmann', 'adler', 'compliance', 'Corporate and tax recordkeeping questions'),
    ('adler', 'sug', 'compliance', 'Compliance evidence and unresolved questions'),
]
TOURS = [
    ('Gather evidence', 'Research and intelligence provide reproducible experiments and cited observations. Missing coverage stays visible.', ['research']),
    ('Evaluate independently', 'Three permanent strategy roles evaluate within existing mandates. A candidate is not an order or a return promise.', ['evaluation']),
    ('Apply independent gates', 'Anna reviews another worker’s evidence. Friedrich can veto. Deterministic risk checks and current eligibility remain mandatory.', ['review', 'risk']),
    ('Improve with evidence', 'Measured costs inform bounded engineering. Validation, actual push, authorized deployment and operational adoption are separate gates.', ['engineering']),
    ('Report and reconcile', 'Accounting and compliance evidence reaches coordination. Sug reports verified facts and unresolved gaps to the owner.', ['reporting', 'compliance']),
]


def scene(catalog):
    if set(catalog) != set(POSITIONS):
        raise ValueError('Exact public fifteen-role registry required')
    nodes = [{**row, 'id': identity, 'x': POSITIONS[identity][0], 'y': POSITIONS[identity][1]}
             for identity, row in catalog.items()]
    by_id = {n['id']: n for n in nodes}
    anchors = {**by_id, 'owner': {'x': 115, 'y': 90}}
    edges = [(identity, row['manager'], 'reporting', 'Defined reporting responsibility')
             for identity, row in catalog.items()] + HANDOFFS
    links = []
    for index, (source, target, kind, label) in enumerate(edges):
        first, last = anchors[source], anchors[target]
        middle = (first['y']+last['y'])/2
        if first['y'] == last['y']:
            middle -= 100
        links.append({'id': str(index), 'source': source, 'target': target, 'kind': kind,
                      'label': label, 'x1': first['x'], 'y1': first['y'],
                      'x2': last['x'], 'y2': last['y'], 'middle': middle,
                      'relationship': 'registry hierarchy' if index < 15 else 'conceptual handoff'})
    return {'nodes': nodes, 'links': links, 'actual_transfers_verified': False,
            'tours': [{'title': title, 'description': description, 'kinds': kinds}
                      for title, description, kinds in TOURS]}


def svg(value):
    parts = ['<svg id="flow-svg" viewBox="0 0 1260 920" role="group" aria-labelledby="flow-map-title flow-map-description">',
             '<title id="flow-map-title">Conceptual team responsibilities and evidence handoffs</title>',
             '<desc id="flow-map-description">Fifteen software roles. Select a role with the keyboard or worker selector. Paths illustrate responsibility, not observed network traffic.</desc>',
             '<defs><linearGradient id="flow-card" x2="1" y2="1"><stop stop-color="#182723"/><stop offset="1" stop-color="#0c1111"/></linearGradient><radialGradient id="flow-halo"><stop stop-color="#d7ff38" stop-opacity=".1"/><stop offset="1" stop-color="#d7ff38" stop-opacity="0"/></radialGradient></defs>',
             '<ellipse cx="650" cy="360" rx="540" ry="350" fill="url(#flow-halo)"/>',
             '<g class="flow-grid" aria-hidden="true">'+''.join(f'<path d="M 20 {y} H 1240"/>' for y in (180,410,635,900))+'</g>',
             '<g class="flow-owner"><circle cx="115" cy="80" r="28"/><text x="115" y="84">OWNER</text><text x="115" y="125">Capital &amp; live authority</text></g>',
             '<g id="flow-paths" aria-hidden="true">']
    for edge in value['links']:
        parts.append(f'<path id="flow-route-{edge["id"]}" class="flow-route {edge["kind"]}" d="M {edge["x1"]} {edge["y1"]} C {edge["x1"]} {edge["middle"]}, {edge["x2"]} {edge["middle"]}, {edge["x2"]} {edge["y2"]}"/>')
    parts.append('</g><g id="flow-particles" aria-hidden="true">'+''.join(f'<circle id="flow-particle-{i}" r="3" visibility="hidden"/>' for i in range(24))+'</g>')
    for node in value['nodes']:
        first, last = node['name'].rsplit(' ', 1) if ' ' in node['name'] else (node['name'], 'COORDINATION')
        identity = node['id']
        parts.append(f'<g class="flow-node" id="flow-node-{identity}" data-worker="{identity}" tabindex="0" role="button" aria-label="{escape(node["name"])} — {escape(node["purpose"])}" aria-pressed="false" transform="translate({node["x"]-86},{node["y"]-46})"><title>{escape(node["purpose"])}</title><rect width="172" height="92" rx="10"/><path class="flow-node-accent" d="M 15 0 H 65"/><text class="flow-node-role" x="15" y="20">{escape(identity.upper())}</text><text class="flow-node-first" x="15" y="44">{escape(first)}</text><text class="flow-node-last" x="15" y="68">{escape(last)}</text><circle cx="153" cy="18" r="3" class="flow-role-dot"/></g>')
    parts.append('</svg>')
    return ''.join(parts)

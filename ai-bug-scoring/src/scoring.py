"""System A2: check the factors an agent recorded for one bug, add the points, render the comment.

A pure module, with no I/O: apply-scores.py and the tests import it.
"""

IMPACT = {
    'data': (40, 'Content loss or data corruption'),
    'unstable': (40, 'Erratic in production'),
    'siteDown': (40, 'Site fully broken'),
    'sitePartial': (30, 'Visitors partly impacted'),
    'editorBlocked': (20, 'Editors blocked'),
    'devBlocked': (20, 'Developers blocked'),
    'hindered': (4, 'Slowed down, not blocked'),
    'cosmetic': (1, 'Cosmetic or wording'),
}
P1 = {'data', 'unstable', 'siteDown'}
REACH = {'high': 15, 'medium': 5, 'low': 0}
WORKAROUND = {'none': 8, 'painful': 4, 'unknown': 4, 'easy': 0}
REGRESSION, PER_CUSTOMER, MAX_CUSTOMERS, CLEAR, CLOUD, OLDER = 5, 5, 3, 6, 3, -5
# The score field holds one number, and A2 sorts every P1 case first: the field adds this to a P1
# score, so sorting the bugs by the field gives the A2 order.
P1_OFFSET = 100
# The field value of a security bug: out of scope, and never read again.
SECURITY_VALUE = -1

KEYS = {
    'ref': str, 'security': bool, 'impact': str, 'feature': str, 'reach': str, 'workaround': str,
    'regression': bool, 'clear': bool, 'cloud': bool, 'older_version_only': bool,
    'customers': int, 'confidence': str, 'why': str,
}
CONFIDENCE = {'high', 'medium', 'low'}


def check(factors, ref):
    """Return the list of problems of one factors object; an empty list means it can be scored."""
    if not isinstance(factors, dict):
        return ['not a JSON object']
    problems = []
    for key, kind in KEYS.items():
        value = factors.get(key)
        # bool is a subclass of int: a customers count of true is a mistake, not 1.
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            problems.append(f'{key}: expected {kind.__name__}, got {value!r}')
    if problems:
        return problems
    if factors['ref'] != ref:
        problems.append(f'ref: expected {ref}, got {factors["ref"]}')
    for key, allowed in (('impact', IMPACT), ('reach', REACH), ('workaround', WORKAROUND),
                         ('confidence', CONFIDENCE)):
        if factors[key] not in allowed:
            problems.append(f'{key}: {factors[key]!r} is not one of {sorted(allowed)}')
    if factors['customers'] < 0:
        problems.append(f'customers: {factors["customers"]} is negative')
    return problems


def score(factors, labels):
    """Return (points, rows, p1). The labels decide the customer gate and the cloud label."""
    customer_label = 'customer' in labels
    customers = min(MAX_CUSTOMERS, max(1, factors['customers'])) if customer_label else 0
    cloud = factors['cloud'] or 'cloud' in labels
    regression = factors['regression'] or 'regression' in labels
    impact_points, impact_label = IMPACT[factors['impact']]
    rows = [
        ('Impact', impact_label, impact_points),
        ('Reach', f'{factors["reach"].capitalize()} ({factors["feature"]})', REACH[factors['reach']]),
        ('Workaround', factors['workaround'].capitalize(), WORKAROUND[factors['workaround']]),
        ('Regression', 'Yes' if regression else 'No', REGRESSION if regression else 0),
        ('Customers', str(customers) if customer_label else 'No customer label', PER_CUSTOMER * customers),
        ('Expected behaviour clear', 'Yes' if factors['clear'] else 'No', CLEAR if factors['clear'] else 0),
        ('Jahia Cloud', 'Yes' if cloud else 'No', CLOUD if cloud else 0),
        ('Only older versions', 'Yes' if factors['older_version_only'] else 'No',
         OLDER if factors['older_version_only'] else 0),
    ]
    return sum(row[2] for row in rows), rows, factors['impact'] in P1


def field_value(points, p1):
    """The number written to the score field."""
    return points + P1_OFFSET if p1 else points


def render_comment(marker, points, rows, p1, factors, agent, run_url, date):
    """The breakdown comment posted on the ticket."""
    value = field_value(points, p1)
    lines = [
        marker,
        '> [!NOTE]',
        f'> **🤖 PM score: {value}** · system A2 · {date} · *a suggestion for the PM decision*',
        '',
    ]
    if p1:
        lines += [f'**P1 case:** it goes before every other bug. The field value is {P1_OFFSET} + {points} points.', '']
    lines += ['| Factor | Value | Points |', '|---|---|---|']
    lines += [f'| {name} | {text} | {pts:+d} |' if pts else f'| {name} | {text} | 0 |' for name, text, pts in rows]
    lines += [f'| **Total** | | **{points}** |', '']
    lines += [f'**Why:** {factors["why"]}', '']
    if factors['confidence'] == 'low':
        lines += ['The agent was not sure about the impact: please check it.', '']
    lines += [f'<sub>Scored by {agent} · [run]({run_url}). A wrong factor? Fix the field value by hand: the job never overwrites a value.</sub>']
    return '\n'.join(lines) + '\n'

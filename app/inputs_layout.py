"""Which measurement inputs are active, from the DIP-switch configuration.

Mirrors the touchscreen's Power screen (ttne-display scr_power.c): the
branch and system type decide how many branches and phases exist, and input
``line_id`` (1-based) = branch * phases + phase + 1.

Neutral has no measurement of its own on this hardware, so "three-phase with
neutral" shows the same three phase inputs as "three-phase without neutral".
"""
from django.utils.translation import gettext as _

PHASES_BY_SYS_TYPE = {0: 1, 1: 2, 2: 3, 3: 3}   # single, bi, 3-phase, 3-phase + N
BRANCHES_BY_BRANCH = {0: 1, 1: 2}                # Main, Main + Aux


def _type_label(sys_type):
    return {
        0: _('Single-phase'),
        1: _('Bi-phase'),
        2: _('Three-phase without neutral'),
        3: _('Three-phase with neutral'),
    }[sys_type]


def _current_type_label(curr_type):
    return {
        0: _('Hall sensor (Melexis)'),
        1: _('Current transformer'),
    }[curr_type]


def build_layout(switches):
    """Return the layout for the given inputs/switches response, or None.

    ``switches`` is the PDU's {"branch", "sys_type", "curr_type"} dict. The
    result is JSON-ready and is what the browser renders.
    """
    if not isinstance(switches, dict):
        return None
    branch = switches.get('branch')
    sys_type = switches.get('sys_type')
    curr_type = switches.get('curr_type')
    n_branches = BRANCHES_BY_BRANCH.get(branch)
    n_phases = PHASES_BY_SYS_TYPE.get(sys_type)
    if n_branches is None or n_phases is None:
        return None

    branches = []
    for b in range(n_branches):
        name = _('Main branch') if b == 0 else _('Aux branch')
        phases = [
            {'line_id': b * n_phases + p + 1, 'label': f'L{p + 1}'}
            for p in range(n_phases)
        ]
        branches.append({'name': name, 'phases': phases})

    return {
        'branch_label': _('Main branch') if n_branches == 1 else _('Main and aux branches'),
        'type_label': _type_label(sys_type),
        'current_type_label': (_current_type_label(curr_type)
                               if curr_type in (0, 1) else ''),
        'branches': branches,
        'active_line_ids': [p['line_id'] for br in branches for p in br['phases']],
    }

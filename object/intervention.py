# -*- coding: utf-8 -*-
################################################################################
#
# Computerized maintenance management system (CMMS) module,
# Copyright (C)
#    Nextma (http://www.nextma.com). All Right Reserved
#    2005 - 2011 Héonium (http://heonium.com). All Right Reserved
#
# CMMS module is free software: you can redistribute
# it and/or modify it under the terms of the Affero GNU General Public License
# as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# CMMS module is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the Affero GNU
# General Public License for more details.
#
# You should have received a copy of the Affero GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################

import time
from fnx import Normalize
from osv import fields, osv
from tools import config
from tools.translate import _
import tools

PRIORITIES = [
    ('normal','Normal'),
    ('low','Low'),
    ('urgent','Urgent'),
    ('other','Other'),
    ]

REQUEST_TYPES = [
    ('check','Check'),
    ('repair','Repair'),
    ('overhaul','Overhaul'),
    ('other','Other'),
    ]

class cmms_intervention(Normalize, osv.osv):
    _name = "cmms.intervention"
    _description = "Intervention request"

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['ref_num'] = False
        return super(cmms_intervention, self).copy(cr, uid, id, default=default, context=context)

    def create(self, cr, user, vals, context=None):
        if 'ref_num' not in vals or not vals['ref_num']:
            vals['ref_num'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.intervention')
        machines = self.pool.get('cmms.equipment')
        machine = machines.browse(cr, 1, vals['equipment_id'])
        vals['name'] = ("%s - %s - %s - %s" % (vals['ref_num'], vals['type'], machine.name.strip(), vals['description'] or '')).strip(' -')
        return super(cmms_intervention, self).create(cr, user, vals, context)

    _columns = {
        'name': fields.char('Name', size=64),
        'ref_num': fields.char('Reference', size=64, select=True),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'date': fields.datetime('Date'),
        'user_id': fields.many2one('res.users', 'Sender', domain="[('groups_id.category_id.name','=','CMMS')]"),
        'user2_id': fields.many2one('res.users', 'Recipient', domain="[('groups_id.category_id.name','=','CMMS')]"),
        'priority': fields.selection(PRIORITIES,'Priority', size=32),
        'observation': fields.text('Observation'),
        'date_inter': fields.datetime('Request date'),
        'date_end': fields.datetime('Completion date'),
        'type': fields.selection(REQUEST_TYPES,'Request type', size=32),
        'time': fields.float('Duration (in hours)'),
        'description': fields.char('Description', size=64),
    }
    _defaults = {
        'type': lambda * a:'repair',
        'priority': lambda * a:'normal',
        'user_id': lambda object,cr,uid,context: uid,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    _sql_constraints = [
            ('intervention_ref_key', 'unique(ref_num)', 'CM reference already exists'),
            ]
    _constraints = [
            (lambda s, *a: s.check_unique('ref_num', *a), '\nCM reference already exists', ['ref_num']),
            ]
cmms_intervention()

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

import base64
import time
import tools
from osv import fields,osv,orm

import mx.DateTime
from mx.DateTime import RelativeDateTime, today, DateTime, localtime
from oe_utils import Normalize
from tools import config
from tools.translate import _

PRIORITIES = [
    ('3','Normal'),
    ('2','Low'),
    ('1','High'),
    ]

STATES = [
    ('draft','Draft'),
    ('confirmed','Confirmed'),
    ('done','Done'),
    ]

class cmms_request_link(Normalize, osv.osv):
    _name = 'cmms.request.link'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'object': fields.char('Object', size=64, required=True),
        'priority': fields.integer('Priority'),
    }
    _defaults = {
        'priority': lambda *a: 5,
    }
    _order = 'priority'

cmms_request_link()

class cmms_incident(Normalize, osv.osv):
    _name = "cmms.incident"
    _description = "Incident" 
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['reference'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.incident')
        return super(cmms_incident, self).copy(cr, uid, id, default=default, context=context)

    def create(self, cr, user, vals, context=None):
        if 'reference' not in vals or not vals['reference']:
            vals['reference'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.incident')
        return super(cmms_incident, self).create(cr, user, vals, context)

    def _links_get(self, cr, uid, context={}):
        obj = self.pool.get('cmms.request.link')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['object', 'name'], context)
        return [(r['object'], r['name']) for r in res]

    def onchange_ref_id(self, cr, uid, ids, id, context={}):
        if not id:
            return {}
        table, id = id.split(',')
        id = int(id)
        record = self.pool.get(table).browse(cr, uid, [id])[0]
        liste = self.pool.get('cmms.question').search(cr, uid, [('checklist_id', '=', id)])
        return {'value':{'equipment_id': record.equipment_id.id}}

    _columns = {
        'reference':fields.char('Work order reference',size=64),
        'state': fields.selection(STATES,'State', size=32),
        'priority': fields.selection(PRIORITIES, 'Priority'),
        'user_id': fields.many2one('res.users', 'Assigned to'),
        'date': fields.datetime('Work order date'),
        'active' : fields.boolean('Active?'),
        'ref' : fields.reference('Work order source', selection=_links_get, size=128),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'archiving3_ids': fields.one2many('cmms.archiving3', 'incident_id', 'follow-up history'),
    }
    _defaults = {
        'active': lambda *a: True,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'priority': lambda *a: PRIORITIES[2][0],
        'user_id': lambda obj,cr,uid,context: uid,
        'state': lambda *a: 'draft',
    }
    _sql_constraints = [
            ('incident_ref_key', 'unique(reference)', 'Work Order reference already exists'),
            ]
    _constraints = [
            (lambda s, *a: s.check_unique('reference', *a), '\nWork Order reference already exists', ['reference']),
            ]
cmms_incident()

class cmms_archiving3(Normalize, osv.osv):
    _name = "cmms.archiving3"
    _description = "Incident follow-up history"

    _columns = {
        'name': fields.char('Object', size=32, required=True),
        'date': fields.datetime('Date'),
        'description': fields.text('Description'),
        'incident_id': fields.many2one('cmms.incident', 'Incident',required=True),
        'user_id': fields.many2one('res.users', 'Assigned to', readonly=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda object,cr,uid,context: uid,
    }

cmms_archiving3()

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

from fnx import Normalize, xrange, one_day
from fnx.dbf import Date, RelativeDay, RelativeMonth
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
    _inherit = ['mail.thread']
    _order = 'date desc'
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['ref_num'] = False
        return super(cmms_incident, self).copy(cr, uid, id, default=default, context=context)

    def create(self, cr, user, vals, context=None):
        if 'ref_num' not in vals or not vals['ref_num']:
            vals['ref_num'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.incident')
        vals['name'] = "%s - %s" % (vals['ref_num'], vals['description'])
        wo_id = super(cmms_incident, self).create(cr, user, vals, context)
        partner_ids = [id for id in set([user, vals['user_id']]) if id]
        self.message_subscribe_users(cr, user, [wo_id], partner_ids, context=context)
        return wo_id

    def _links_get(self, cr, uid, context=None):
        obj = self.pool.get('cmms.request.link')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['object', 'name'], context=context)
        return [(r['object'], r['name']) for r in res]

    def onchange_ref_id(self, cr, uid, ids, ref_id, context={}):
        if not ref_id:
            return {}
        table, ref_id = ref_id.split(',')
        ref_id = int(ref_id)
        record = self.pool.get(table).browse(cr, uid, [ref_id])[0]
        liste = self.pool.get('cmms.question').search(cr, uid, [('checklist_id', '=', ref_id)])
        return {'value':{'equipment_id': record.equipment_id.id}}

    def search(self, cr, user, args=None, offset=0, limit=None, order=None, context=None, count=False):
        # 2013 08 12  (yyyy mm dd)
        new_args = []
        for arg in args:
            if not isinstance(arg, list) or arg[0] != 'date' or arg[2] not in ['THIS_WEEK', 'LAST_WEEK', 'THIS_MONTH', 'LAST_MONTH']:
                new_args.append(arg)
                continue
            today = Date.today()
            period = arg[2]
            if period == 'THIS_WEEK':
                start = today.replace(day=RelativeDay.LAST_MONDAY)
                stop = start.replace(delta_day=6)
            elif period == 'LAST_WEEK':
                start = today.replace(day=RelativeDay.LAST_MONDAY, delta_day=-7)
                stop = start.replace(delta_day=6)
            elif period == 'THIS_MONTH':
                start = today.replace(day=1)
                stop = start.replace(delta_month=1, delta_day=-1)
            elif period == 'LAST_MONTH':
                start = today.replace(day=1, delta_month=-1)
                stop = start.replace(delta_month=1, delta_day=-1)
            else:
                raise ValueError("forgot to update something! (period is %r)" % (arg[2],))
            op = arg[1]
            if arg[1] in ('=', 'in'):
                op = '&'
                first = '>='
                last = '<='
            elif arg[1] in ('!=', 'not in'):
                op = '|'
                first = '<'
                last = '>'
            if op != arg[1]:
                new_args.append(op)
                new_args.append(['date', first, start.strftime('%Y-%m-%d')])
                new_args.append(['date', last, stop.strftime('%Y-%m-%d')])
            elif '<' in op:
                new_args.append(['date', op, start.strftime('%Y-%m-%d')])
            elif '>' in op:
                new_args.append(['date', op, last.strftime('%Y-%m-%d')])
            else:
                raise ValueError('unable to process domain: %r' % arg)
        return super(cmms_incident, self).search(cr, user, args=new_args, offset=offset, limit=limit, order=order, context=context, count=count)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('user_id') and vals['user_id']:
            self.message_subscribe_users(cr, uid, ids, [vals['user_id']], context=context)
        return super(cmms_incident, self).write(cr, uid, ids, vals, context=context)

    _columns = {
        'name': fields.char('Name', size=64),
        'ref_num':fields.char('Reference',size=64),
        'description': fields.char('Description', size=64, required=True),
        'state': fields.selection(STATES,'State', size=32),
        'priority': fields.selection(PRIORITIES, 'Priority'),
        'user_id': fields.many2one('res.users', 'Assigned to', domain="[('groups_id.category_id.name','=','CMMS')]"),
        'date': fields.datetime('Date'),
        'ref' : fields.reference('Source', selection=_links_get, size=128),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'archiving3_ids': fields.one2many('cmms.archiving3', 'incident_id', 'follow-up history', ondelete='cascade'),
        'time': fields.float('Duration (in hours)'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'priority': lambda *a: PRIORITIES[2][0],
        'user_id': lambda obj,cr,uid,context: uid,
        'state': lambda *a: 'draft',
    }
    _sql_constraints = [
            ('incident_ref_key', 'unique(ref_num)', 'Work Order reference already exists'),
            ]
    _constraints = [
            (lambda s, *a: s.check_unique('ref_num', *a), '\nWork Order reference already exists', ['ref_num']),
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

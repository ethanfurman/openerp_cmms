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


from dateutil.relativedelta import *
from fnx import xrange, one_day
from fnx.openerp import Normalize
from fnx.dbf import Date, RelativeDay, RelativeMonth
from openerp import SUPERUSER_ID
from osv.osv import except_osv as ERPError
from osv import fields, osv, orm
from tools import config
from tools.translate import _
import base64
import datetime
import logging
import math
import math
import pooler
import time
import tools

_logger = logging.getLogger(__name__)

YESNO = [
    ('yes','Yes'),
    ('no','No'),
    ]

STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('done', 'Done'),
    ]

HELP_PRIORITIES = [
    ('normal','Normal'),
    ('low','Low'),
    ('urgent','Urgent'),
    ('other','Other'),
    ]

HELP_REQUEST_TYPES = [
    ('check','Check'),
    ('repair','Repair'),
    ('overhaul','Overhaul'),
    ('other','Other'),
    ]

WO_PRIORITIES = [
    ('3','Normal'),
    ('2','Low'),
    ('1','High'),
    ]

#
# Production Line
#
class cmms_line(Normalize, osv.Model):
    "production line"
    _name = 'cmms.line'
    _description = 'Production line'
    _order = 'name asc'

    _columns = {
        'name': fields.char('Production line', size=64, required=True),
        'ref_num': fields.char('Inventory ID', size=64),
        'location': fields.char('Location', size=64),
        'sequence': fields.integer('Sequence'),
        'equipment_ids': fields.one2many('cmms.equipment', 'line_id', 'Equipment'),
        }
    _sql_constraints = [
        ('line_ref_key', 'unique(ref_num)', 'Line inventory tag already exists'),
        ('line_name_key', 'unique(name)', 'Line name already exists'),
        ]
    _constraints = [
        (lambda s, *a: s.check_unique('ref_num', *a), '\nLine inventory tag already exists', ['name']),
        (lambda s, *a: s.check_unique('name', *a), '\nLine name already exists', ['name']),
        ]

    def create(self, cr, user, vals, context=None):
        if 'ref_num' not in vals or not vals['ref_num']:
            vals['ref_num'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.line')
        if 'name' not in vals or not vals['name']:
            vals['name'] = vals['ref_num']
        return super(cmms_line, self).create(cr, user, vals, context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['ref_num'] = False
        default['name'] = False
        return super(cmms_line, self).copy(cr, uid, id, default=default, context=context)


#
# Equipment
#
class cmms_equipment(Normalize, osv.Model):
    "equipment"
    _name = "cmms.equipment"
    _description = "equipment"
    _order = 'name asc'

    _columns = {
        'name': fields.char('Machine', size=64, required=True),
        'inv_tag': fields.char('Inventory ID', size=64),
        'trademark': fields.char('Make', size=64),
        'model': fields.char('Model', size=64),
        'serial': fields.char('Serial Number', size=64),
        'line_id': fields.many2one('cmms.line','Production Line', required=True, change_default=True),
        'startingdate': fields.datetime("Start Date"),
        'product_ids': fields.many2many(
            'product.product',
            'product_equipment_rel',
            'product_id',
            'equipment_id',
            string='Spare Parts',
            domain="[('categ_id','child_of','Spare Parts')]",
            ),
        'deadlinegar': fields.datetime("Warranty Expiration"),
        'description': fields.text('Description'),
        'safety': fields.text('Safety Instruction'),
        'user_id': fields.many2one(
            'res.users',
            'Assigned to',
            domain="[('groups_id.category_id.name','=','CMMS'),('groups_id.name','=','User')]",
            ),
        'work_order_ids': fields.one2many('cmms.incident', 'equipment_id', 'Work Order History'),
        'help_request_ids': fields.one2many('cmms.intervention', 'equipment_id', 'Help Request History'),
        'pm_ids': fields.one2many('cmms.pm', 'equipment_id', 'Preventive Maintenance History'),
        'cm_ids': fields.one2many('cmms.cm', 'equipment_id', 'Corrective Maintenance History'),
        }
    _defaults = {
        'user_id': lambda object,cr,uid,context: uid,
        }
    _sql_constraints = [
        ('equipment_ref_key', 'unique(inv_tag)', 'Machine inventory ID already exists'),
        ]
    _constraints = [
        (lambda s, *a: s.check_unique('inv_tag', *a), '\nMachine inventory ID already exists', ['inv_tag']),
        ]

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['inv_tag'] = False
        default['name'] = False
        return super(cmms_equipment, self).copy(cr, uid, id, default=default, context=context)

    def create(self, cr, user, vals, context=None):
        if 'inv_tag' not in vals or not vals['inv_tag']:
            vals['inv_tag'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.equipment')
        if 'name' not in vals or not vals['name']:
            vals['name'] = vals['inv_tag']
        return super(cmms_equipment, self).create(cr, user, vals, context)


#
# Corrective Maintenance / Failures / Breakdowns
#
class cmms_failure(Normalize, osv.Model):
    "failure cause"
    _name = "cmms.failure"
    _description = "failure cause"
    _columns = {
        'name': fields.char('Type of Failure', size=32, required=True),
        'code': fields.char('Code', size=32),
        'description': fields.text('Description'),
        }
    def create(self, cr, uid, vals, context=None):
        if 'code' not in vals or not vals['code']:
            vals['code'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.failure')
        return super(cmms_failure, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['code'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.failure')
        return super(cmms_failure, self).copy(cr, uid, id, default=default, context=context)


class cmms_diagnosistab(Normalize, osv.Model):
    "failure resolution"
    _name = "cmms.diagnosistab"
    _description = "Diagnostics List"
    _columns = {
        'name': fields.char('Failure Causes', size=32, required=True),
        'solution': fields.text('Solution'),
        'cm_id': fields.many2one('cmms.cm', 'Corrective Maintenance'),
        }


class cmms_cm(Normalize, osv.Model):
    "corrective (unplanned) maintenance"

    _name = "cmms.cm"
    _description = "Corrective Maintenance System"
    _columns = {
        'name': fields.char('Name', size=64),
        'ref_num': fields.char('CM Reference', size=20),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'failure_id': fields.many2one('cmms.failure', 'Failure?', required=True),
        'date': fields.datetime('Date'),
        'note': fields.text('Notes'),
        'user_id': fields.many2one('res.users', 'Responsible', domain="[('groups_id.category_id.name','=','CMMS'),('groups_id.name','=','Staff')]"),
        'diagnosistab_ids': fields.one2many('cmms.diagnosistab', 'cm_id', 'Diagnostic Table'),
        'archiving_ids': fields.one2many('cmms.archiving', 'cm_id', 'Follow-up History'),
        }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda object,cr,uid,context: uid,
        }
    _sql_constraints = [
        ('cm_ref_key', 'unique(ref_num)', 'CM Reference already exists'),
        ]
    _constraints = [
        (lambda s, *a: s.check_unique('ref_num', *a), '\nCM Reference already exists', ['ref_num']),
        ]

    def create(self, cr, uid, vals, context=None):
        if 'ref_num' not in vals or not vals['ref_num']:
            vals['ref_num'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.cm')
        machines = self.pool.get('cmms.equipment')
        machine = machines.browse(cr, uid, vals['equipment_id'])
        failures = self.pool.get('cmms.failure')
        failure = failures.browse(cr, uid, vals['failure_id'])
        vals['name'] = "%s - %s - %s" % (vals['ref_num'], machine.name.strip(), failure.name.strip())
        return super(cmms_cm, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['ref_num'] = False
        return super(cmms_cm, self).copy(cr, uid, id, default=default, context=context)


class cmms_archiving(Normalize, osv.Model):
    "corrective maintenance archive"
    _name = "cmms.archiving"
    _description = "CM follow-up History"
    _columns = {
        'name': fields.char('Effect', size=32, required=True),
        'date': fields.datetime('Date'),
        'description': fields.text('Description'),
        'cm_id': fields.many2one('cmms.cm', 'Archiving',required=True),
        }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }


#
# Preventive Maintenance / Scheduled Downtime
#
class cmms_pm(Normalize, osv.osv):
    "preventive (planned) maintenance"

    def _calc_days(self, cr, uid, ids, field_names, arg, context):
        res = {}
        if ids:
            records = self.read(
                    cr, uid, ids,
                    ['id', 'name', 'days_interval', 'days_last_done', 'days_left', 'days_warn_period', 'meter'],
                    context,
                    )
            for record in records:
                id = record['id']
                res[id] = {}
                if record['meter'] == "days":
                    interval = datetime.timedelta(days=record['days_interval'])
                    last_done = record['days_last_done']
                    last_done = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_done, "%Y-%m-%d")))
                    next_due = last_done + interval
                    res[id]['days_next_due'] = next_due.strftime("%Y-%m-%d")
                    now = datetime.datetime.now()
                    due_days = next_due - now
                    res[id]['days_left'] = due_days.days
                    if due_days.days <= 0:
                        res[id]['state'] = 'Overdue'
                    elif due_days.days <= record['days_warn_period']:
                        res[id]['state'] = 'Approaching'
                    else:
                        res[id]['state'] = 'OK'
                else:
                    _logger.error('record <%s - %s> does not have a meter of "days"', id, record['name'])
                    del res[id]
        return res

    def _calc_name(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for id in (ids or []):
            machines = self.pool.get('cmms.equipment')
            for record in self.read(cr, uid, ids, ['id', 'ref_num', 'description', 'equipment_id'], context=context):
                machine = machines.read(cr, SUPERUSER_ID, [('id','=',record['equipment_id'][0])], context=context)[0]
                res[id] = "%s - %s - %s" % (record['ref_num'], machine['name'].strip(), record['description'])
        return res

    def _get_pm_ids_from_equipment(equipment_table, cr, uid, ids, context=None):
        self = equipment_table.pool.get('cmms.pm')
        res = self.read(cr, uid, [('equipment_id','in',ids)], context=context)
        return [r['id'] for r in res]

    def _set_calc_fields(self, cr, uid, ids, field_name, field_value, arg, context):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for id in ids:
            cr.execute('UPDATE cmms_pm SET %s=%%s where id=%%s' % field_name, (field_value, id))
        return True

    def update_time_remaining(self, cr, uid, ids=None, fields=None, arg=None, context=None):
        if ids is None:
            ids = self.search(cr, uid, [], context=context)
        for id, values in self._calc_days(cr, uid, ids, ['days_left', 'state'], (), context=context).items():
            if not self.write(cr, uid, id, {'days_left': values['days_left'], 'state': values['state']}):
                _logger.error('unable to update cmms.pm::%s -- %s', values['id'], values['name'])
        return True

    _name = "cmms.pm"
    _description = "Preventive Maintenance System"
    _order = 'days_left asc, name asc'

    _columns = {
        'name': fields.function(
            _calc_name,
            method=True,
            type='char',
            size=96,
            string='Name',
            store={
                'cmms.pm': (lambda table, cr, uid, ids, ctx={}: ids, ['ref_num', 'description'], 20),
                'cmms.equipment': (_get_pm_ids_from_equipment, ['name'], 10),
                },
            ),
        'ref_num': fields.char('PM Reference', size=20, select=True),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'description': fields.char('Description', size=64),
        'meter': fields.selection([ ('days', 'Days')], 'Unit of measure'),
        'recurrent': fields.boolean('Recurrent ?', help="Mark this option if PM is periodic"),
        'days_interval': fields.integer('Interval'),
        'days_last_done': fields.date('Last done', required=True),
        'days_warn_period': fields.integer('Warning time'),
        'days_next_due': fields.function(
            _calc_days,
            method=True,
            type="date",
            string='Next service date',
            store={
                'cmms.pm': (lambda table, cr, uid, ids, ctx: ids, ['days_interval', 'days_last_done'], 10),
                },
            multi='calc',
            ),
        'days_left': fields.function(
            _calc_days,
            fnct_inv=_set_calc_fields,
            method=True,
            type="integer",
            string='Days until next service',
            store={
                'cmms.pm': (lambda table, cr, uid, ids, ctx: ids, ['days_interval', 'days_last_done'], 10),
                },
            multi='calc',
            ),
        'state': fields.function(
            _calc_days,
            fnct_inv=_set_calc_fields,
            method=True,
            type="char",
            size=12,
            string='Status',
            store={
                'cmms.pm': (lambda table, cr, uid, ids, ctx: ids, ['days_interval', 'days_last_done', 'days_warn_period'], 10),
                },
            multi='calc',
            ),
        'archiving2_ids': fields.one2many('cmms.archiving2', 'pm_id', 'follow-up history'),
        'note': fields.text('Notes'),
        }

    _defaults = {
        'meter': lambda * a: 'days',
        'recurrent': lambda * a: True,
        'days_last_done': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    _sql_constraints = [
        ('pm_ref_key', 'unique(ref_num)', 'PM reference already exists'),
        ]

    _constraints = [
        (lambda s, *a: s.check_unique('ref_num', *a), '\nPM reference already exists', ['ref_num']),
        ]

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
            default = default.copy()
        default['ref_num'] = False
        return super(cmms_pm, self).copy(cr, uid, id, default=default, context=context)

    def create(self, cr, user, vals, context=None):
        if 'ref_num' not in vals or not vals['ref_num']:
            vals['ref_num'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.pm')
        return super(cmms_pm, self).create(cr, user, vals, context)


class cmms_archiving2(Normalize, osv.Model):
    "preventative maintenance archive"

    _name = "cmms.archiving2"
    _description = "PM follow-up history"
    _columns = {
        'name': fields.char('Effect', size=32, required=True),
        'date': fields.datetime('Date'),
        'description': fields.text('Description'),
        'pm_id': fields.many2one('cmms.pm', 'Archiving',required=True),
        }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }


#
# Work Orders
#
class cmms_request_link(Normalize, osv.Model):
    "work order request"
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


class cmms_incident(Normalize, osv.Model):
    "work order"
    _name = "cmms.incident"
    _description = "Incident"
    _inherit = ['mail.thread']
    _order = 'date desc'

    def _days_due(self, cr, uid, ids, prop, unknown_none, context):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        for wo in self.browse(cr, uid, ids, context=context):
            res[wo.id] = False
            if wo.date_due and wo.state != 'done':
                now = Date.today()
                due_days = Date(wo.date_due) - now
                res[wo.id] = due_days.days
        return dict(res)

    def _links_get(self, cr, uid, context=None):
        obj = self.pool.get('cmms.request.link')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['object', 'name'], context=context)
        return [(r['object'], r['name']) for r in res]

    _columns = {
        'name': fields.char('Name', size=64),
        'ref_num':fields.char('Reference',size=64),
        'description': fields.char('Description', size=64, required=True),
        'state': fields.selection(STATES,'State', size=32),
        'priority': fields.selection(WO_PRIORITIES, 'Priority'),
        'user_id': fields.many2one('res.users', 'Assigned to', domain="[('groups_id.category_id.name','=','CMMS'),('groups_id.name','=','Staff')]"),
        'date': fields.datetime('Date'),
        'date_due': fields.date('Due Date', help='Date when servicing must be finished'),
        'days_left': fields.function(
            _days_due,
            method=True,
            type="integer",
            string='Deadline',
            ),
        'ref' : fields.reference('Source', selection=_links_get, size=128),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'archiving3_ids': fields.one2many('cmms.archiving3', 'incident_id', 'follow-up history', ondelete='cascade'),
        'time': fields.float('Duration (in hours)'),
        }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'priority': lambda *a: WO_PRIORITIES[2][0],
        'state': lambda *a: 'draft',
        }
    _sql_constraints = [
        ('incident_ref_key', 'unique(ref_num)', 'Work Order reference already exists'),
        ]
    _constraints = [
        (lambda s, *a: s.check_unique('ref_num', *a), '\nWork Order reference already exists', ['ref_num']),
        ]

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

    def onchange_ref_id(self, cr, uid, ids, ref_id, context={}):
        if not ref_id:
            return {}
        table, ref_id = ref_id.split(',')
        ref_id = int(ref_id)
        record = self.pool.get(table).browse(cr, uid, [ref_id])[0]
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


class cmms_archiving3(Normalize, osv.Model):
    "work-order archive"
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


#
# Help Requests
#
class cmms_intervention(Normalize, osv.Model):
    "help request"
    _name = "cmms.intervention"
    _description = "Intervention request"
    _columns = {
        'name': fields.char('Name', size=64),
        'ref_num': fields.char('Reference', size=64, select=True),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'date': fields.datetime('Date'),
        'user_id': fields.many2one('res.users', 'Sender', domain="[('groups_id.category_id.name','=','CMMS'),('groups_id.name','=','Staff')]"),
        'user2_id': fields.many2one('res.users', 'Recipient', domain="[('groups_id.category_id.name','=','CMMS'),('groups_id.name','=','Staff')]"),
        'priority': fields.selection(HELP_PRIORITIES,'Priority', size=32),
        'observation': fields.text('Observation'),
        'date_inter': fields.datetime('Request date'),
        'date_end': fields.datetime('Completion date'),
        'type': fields.selection(HELP_REQUEST_TYPES,'Request type', size=32),
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


#
# Checklists
#
class cmms_checklist(Normalize, osv.Model):
    "checklist"
    _name="cmms.checklist"
    _description= "checklist"
    _columns={
        'name': fields.char("Title",size=128, required=True),
        'description': fields.text('Description'),
        'questions_ids': fields.one2many("cmms.question","checklist_id","Questions",),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine'),
        }
    _sql_constraints = [
        ('checklist_name_key', 'unique(name)', 'Checklist name already exists'),
        ]
    _constraints = [
        (lambda s, *a: s.check_unique('name', *a), '\nChecklist name already exists', ['name']),
        ]


class cmms_question(Normalize, osv.Model):
    "checklist item"
    _name = "cmms.question"
    _description = "Question"
    _columns = {
        'name': fields.char("Question",size=128, required=True),
        'checklist_id': fields.many2one('cmms.checklist', 'Checklist', required=True),
        }


class cmms_checklist_history(Normalize, osv.Model):
    "checklist history"
    _name="cmms.checklist.history"
    _description= "Checklist History"

    def onchange_checklist_id(self, cr, uid, ids, id, context=None):
        question_ids = self.pool.get('cmms.question').search(cr, uid, [('checklist_id', '=', id)])
        records = self.pool.get('cmms.question').name_get(cr, uid, question_ids)
        results = []
        for id, name in records:
            obj = {'name': name}
            results.append(obj)
        return {'value':{'answers_ids': results}}

    _columns={
        'name': fields.char("Name",size=128, required=True),
        'checklist_id': fields.many2one('cmms.checklist', 'Checklist'),
        'answers_ids': fields.one2many("cmms.answer.history","checklist_history_id","Responses"),
        'date_planned': fields.datetime("Planned Date"),
        'date_end': fields.datetime("Completed Date"),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine'),
        'user_id': fields.many2one('res.users', 'Assigned to', domain="[('groups_id.category_id.name','=','CMMS'),('groups_id.name','=','Staff')]"),
        'status': fields.selection(STATES, "Status"),
        }
    _defaults = {
        'status' : lambda *a: 'draft',
        'user_id': lambda object,cr,uid,context: uid,
        }


class cmms_question_history(Normalize, osv.Model):
    "answer history"
    _name="cmms.answer.history"
    _description= "Answers"
    _columns={
        'name': fields.char("Question",size=128, required=True),
        'checklist_history_id': fields.many2one('cmms.checklist.history', 'Checklist'),
        'answer': fields.selection(YESNO, "Response"),
        'detail': fields.char("Detail",size=128),
        }


# class cmms_certifications(Normalize, osv.Model):
#     "certifications"
#     _name = 'cmms.certifications'
#     _description = 'cmms certifications'
# 
#     _columns = {
#         'name': fields.char('Training', size=64),
#         'description': fields.text('Description'),
#         'last_training': fields.date(
#         'expires': fields.integer('Months', help='Training is good for how long?'),
#         }
# 
# 
# class cmms_training(osv.Model):
#     'training'
#     _name = 'cmms.training'
# 
#     _columns = {
#         'user_id': fields.many2one('res.users', 'User'),


class product_product(osv.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    def _calc_extra_seller(self, cr, uid, ids, fields, arg, context=None):
        result = super(product_product, self)._calc_seller(cr, uid, ids, fields, arg, context=context)
        for product_id, values in result.items():
            main_supplier_id = values['seller_info_id']
            if main_supplier_id:
                main_supplier = self.pool.get('product.supplierinfo').browse(cr, SUPERUSER_ID, main_supplier_id, context=context)
                values.update({
                   'seller_product_name':main_supplier.product_name or False,
                   'seller_product_code':main_supplier.product_code or False,
                })
        return result

    _columns = {
        'seller_product_name': fields.function(_calc_extra_seller, type='char', string='Supplier Product Name', help="Main Supplier's product name.", multi="extra_seller_info"),
        'seller_product_code': fields.function(_calc_extra_seller, type='char', string='Supplier Product Code', help="Main Supplier's product code.", multi="extra_seller_info"),
        'last_order_date': fields.date(string="Last ordered"),
        }

    def create(self, cr, uid, values, context=None):
        if context and context.get('form_view_ref') == 'cmms.equipment_parts_form':
            categ_id = values.get('categ_id')
            if categ_id:
                category = original = self.pool.get('product.category').browse(cr, uid, categ_id, context=context)
                while category.name != 'Spare Parts':
                    category = category.parent_id
                    if not category:
                        raise ERPError('Invalid category', '<%s> is not a <Spare Parts> category' % original.name)
        return super(product_product, self).create(cr, uid, values, context=context)

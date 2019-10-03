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


from fnx.oe import Normalize
from dbf import Date
from fnx_fs.fields import files
from openerp import SUPERUSER_ID
from openerp.exceptions import ERPError
from osv import fields, osv
import datetime
import logging
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
            vals['ref_num'] = self.pool.get('ir.sequence').next_by_code(cr, user, 'cmms.line', context=context)
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


# Equipment
#
class cmms_equipment(Normalize, osv.Model):
    "equipment"
    _name = "cmms.equipment"
    _description = "equipment"
    _inherit = 'fnx_fs.fs'
    _order = 'name asc'

    _fnxfs_path = 'cmms'

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, return_big=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _has_image(self, cr, uid, ids, name, args, context=None):
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = obj.image != False
        return result

    def init(self, cr):
        # ensure name have been reversed to their proper order
        cr.execute(
                "select column_name, ordinal_position"
                " from information_schema.columns"
                " where table_schema = 'public' and table_name = 'product_equipment_rel';"
                )
        fields = cr.fetchall()
        if len(fields) != 2:
            raise ERPError('product_equipment_rel should have exactly two fields, but actually has %d' % len(fields))
        for field_name, ordinal in fields:
            if field_name == 'equipment_id' and ordinal == 2:
                print 'modifying field names for product_equipment_rel...'
                cr.execute('ALTER TABLE product_equipment_rel RENAME equipment_id TO tmp;')
                cr.execute('ALTER TABLE product_equipment_rel RENAME product_id TO equipment_id;')
                cr.execute('ALTER TABLE product_equipment_rel RENAME tmp TO product_id;')
                print 'done'
                break

        # table_catalog    | table_schema |      table_name       | column_name  | ordinal_position

    _columns = {
        'name': fields.char('Machine', size=64, required=True),
        'inv_tag': fields.char('Inventory ID', size=64),
        'trademark': fields.char('Make', size=64),
        'model': fields.char('Model', size=64),
        'serial': fields.char('Serial Number', size=64),
        'line_id': fields.many2one('cmms.line','Production Line', required=True, change_default=True),
        'startingdate': fields.datetime("Start Date"),
        'parts_ids': fields.many2many(
            'product.product',
            'product_equipment_rel',
            'equipment_id',
            'product_id',
            string='Spare Parts',
            domain=[('categ_id','child_of',fields.ref('cmms.cmms_category_spare_parts'))],
            oldname='product_ids',
            ),
        'deadlinegar': fields.datetime("Warranty Expiration"),
        'description': fields.text('Description'),
        'safety': fields.text('Safety Instruction'),
        'user_id': fields.many2one(
            'res.users',
            'Assigned to',
            domain=[('groups_id','=',fields.ref('cmms.group_cmms_user'))],
            ondelete='set null',
            ),
        'work_order_ids': fields.one2many('cmms.incident', 'equipment_id', 'Work Order History'),
        'help_request_ids': fields.one2many('cmms.intervention', 'equipment_id', 'Help Request History'),
        'pm_ids': fields.one2many('cmms.pm', 'equipment_id', 'Preventive Maintenance History'),
        'cm_ids': fields.one2many('cmms.cm', 'equipment_id', 'Corrective Maintenance History'),
        'doc_ids': fields.many2many(
            'ir.attachment',
            'ir_attachment_cmms_equipment_rel', 'equipment_id', 'attachment_id',
            'Attached Documents',
            order='write_date desc',
            context={'default_res_model': 'cmms.equipment'},
            ),
        'documents': files('general_docs', string='Documents'),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Image",
            help="This field holds the image for this equipment, limited to 1024x1024px"),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image",
            store={
                'cmms.equipment': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'cmms.equipment': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of this contact. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'has_image': fields.function(_has_image, type="boolean"),
        # fnxfs fields
        'fnxfs_sop_files': files('sop_manual', string='SOPs & Manuals'),
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
            vals['inv_tag'] = self.pool.get('ir.sequence').next_by_code(cr, user, 'cmms.equipment', context=context)
        if 'name' not in vals or not vals['name']:
            vals['name'] = vals['inv_tag']
        return super(cmms_equipment, self).create(cr, user, vals, context)


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
            vals['code'] = self.pool.get('ir.sequence').next_by_code(cr, uid, 'cmms.failure', context=context)
        return super(cmms_failure, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['code'] = self.pool.get('ir.sequence').next_by_code(cr, uid, 'cmms.failure', context=context)
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
        'equipment_name': fields.related('equipment_id', 'name', string='Machine Name', type='char', size=128),
        'failure_id': fields.many2one('cmms.failure', 'Failure?', required=True),
        'date': fields.datetime('Date'),
        'note': fields.text('Notes'),
        'user_id': fields.many2one('res.users', 'Responsible', domain=[('groups_id','=',fields.ref('cmms.group_cmms_staff'))]),
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
            vals['ref_num'] = self.pool.get('ir.sequence').next_by_code(cr, uid, 'cmms.cm', context=context)
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
        'cm_id': fields.many2one('cmms.cm', 'Archiving',required=True, ondelete='cascade'),
        }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }


# Preventive Maintenance / Scheduled Downtime
#
class cmms_pm(Normalize, osv.osv):
    "preventive (planned) maintenance"

    def _calc_days(self, cr, uid, ids, field_names, arg, context):
        "days_next_due, days_next_due_year, days_next_due_month, days_left, state"
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
                    res[id]['days_next_due_year'] = next_due.strftime("%Y")
                    res[id]['days_next_due_month'] = next_due.strftime("%Y-%m")
                    now = datetime.datetime.now()
                    due_days = next_due - now
                    res[id]['days_left'] = due_days.days
                    if due_days.days <= 0:
                        res[id]['state'] = 'past'
                    elif due_days.days <= record['days_warn_period']:
                        res[id]['state'] = 'soon'
                    else:
                        res[id]['state'] = 'okay'
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
            if not self.write(cr, uid, id, {'days_left': values['days_left'], 'state': values['state']}, context=context):
                _logger.error('unable to update cmms.pm::%s -- %s', values['id'], values['name'])
        return True

    _name = "cmms.pm"
    _description = "Preventive Maintenance System"
    _inherit = ['fnx_fs.fs']
    _order = 'days_left asc, name asc'

    _fnxfs_path = 'cmms'
    _fnxfs_path_fields = ['name']

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
        'equipment_name': fields.related('equipment_id', 'name', string='Machine Name', type='char', size=128),
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
        'days_next_due_year': fields.function(
            _calc_days,
            fnct_inv=_set_calc_fields,
            method=True,
            type="char",
            size=4,
            string='Next service year',
            store={
                'cmms.pm': (lambda table, cr, uid, ids, ctx: ids, ['days_interval', 'days_last_done'], 10),
                },
            multi='calc',
            ),
        'days_next_due_month': fields.function(
            _calc_days,
            fnct_inv=_set_calc_fields,
            method=True,
            type="char",
            size=7,
            string='Next service manth',
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
            type="selection",
            selection=(('okay','Okay'),('soon','Approaching'),('past','Overdue')),
            sort_order='definition',
            string='Status',
            store={
                'cmms.pm': (lambda table, cr, uid, ids, ctx: ids, ['days_interval', 'days_last_done', 'days_warn_period'], 10),
                },
            multi='calc',
            ),
        'archiving2_ids': fields.one2many('cmms.archiving2', 'pm_id', 'follow-up history'),
        'note': fields.text('Notes'),
        'fnxfs_related_files': files('preventive_maintenance', string='Related Files'),
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
            vals['ref_num'] = self.pool.get('ir.sequence').next_by_code(cr, user, 'cmms.pm', context=context)
        return super(cmms_pm, self).create(cr, user, vals, context)


class cmms_archiving2(Normalize, osv.Model):
    "preventative maintenance archive"

    _name = "cmms.archiving2"
    _description = "PM follow-up history"
    _columns = {
        'name': fields.char('Effect', size=32, required=True),
        'date': fields.datetime('Date'),
        'description': fields.text('Description'),
        'pm_id': fields.many2one('cmms.pm', 'Archiving',required=True, ondelete='cascade'),
        }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }


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
        ids = obj.search(cr, uid, [], context=context)
        res = obj.read(cr, uid, ids, ['object', 'name'], context=context)
        return [(r['object'], r['name']) for r in res]

    _columns = {
        'name': fields.char('Name', size=64),
        'ref_num':fields.char('Reference',size=64),
        'description': fields.char('Description', size=64, required=True),
        'state': fields.selection(STATES,'State', size=32),
        'priority': fields.selection(WO_PRIORITIES, 'Priority'),
        'user_id': fields.many2one('res.users', 'Assigned to', domain=[('groups_id','=',fields.ref('cmms.group_cmms_staff'))]),
        'third_party': fields.char('Outside Service', size=128),
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
        'equipment_name': fields.related('equipment_id', 'name', string='Machine Name', type='char', size=128),
        'equipment_doc_ids': fields.related(
            'equipment_id', 'doc_ids',
            obj='ir.attachment',
            rel='ir_attachment_cmms_equipment_rel', id1='equipment_id', id2='attachment_id',
            type='many2many',
            string='Attached Documents',
            ),
        'archiving3_ids': fields.one2many('cmms.archiving3', 'incident_id', 'follow-up history', ondelete='cascade'),
        'time': fields.float('Duration (in hours)'),
        'release_no': fields.char('Release Number', size=32),
        'part_ids': fields.one2many(
            'cmms.parts_used',
            'incident_id',
            string='Spare Parts',
            ),
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
            vals['ref_num'] = self.pool.get('ir.sequence').next_by_code(cr, user, 'cmms.incident', context=context)
        vals['name'] = "%s - %s" % (vals['ref_num'], vals['description'])
        wo_id = super(cmms_incident, self).create(cr, user, vals, context)
        partner_ids = [id for id in set([user, vals['user_id']]) if id]
        self.message_subscribe_users(cr, user, [wo_id], partner_ids, context=context)
        return wo_id

    def onchange_ref_id(self, cr, uid, ids, ref_id, context=None):
        if not ref_id:
            return {}
        table, ref_id = ref_id.split(',')
        ref_id = int(ref_id)
        record = self.pool.get(table).browse(cr, uid, [ref_id], context=context)[0]
        return {'value':{'equipment_id': record.equipment_id.id}}

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('user_id') and vals['user_id']:
            self.message_subscribe_users(cr, uid, ids, [vals['user_id']], context=context)
        return super(cmms_incident, self).write(cr, uid, ids, vals, context=context)


# parts_used
class cmms_parts_used(osv.Model):
    _name = 'cmms.parts_used'
    _description = 'parts used in work orders'

    _columns = {
        'incident_id': fields.many2one('cmms.incident', 'Work Order'),
        'equipment_id': fields.related(
                'incident_id', 'equipment_id',
                type='many2one',
                obj='cmms.equipment',
                string='Equipment',
                ),
        'part_id': fields.many2one('product.product', 'Part', domain=[('categ_id','child_of',fields.ref('cmms.cmms_category_spare_parts'))]),
        'supplier_id': fields.many2one('product.supplierinfo', string='Supplier'),
        'part_name': fields.related('supplier_id', 'product_name', string='Sup part name', type='char', size=128),
        'part_code': fields.related('supplier_id', 'product_code', string='Sup part code', type='char', size=64),
        'qty': fields.integer('Amount'),
        }

    def onchange_equipment(self, cr, uid, ids, equipment_id, part_id, supplier_id, context=None):
        # equipment_id is always known
        # set the other domains and/or values based on which tidbits of info we
        # have (anything not set will be False)
        cmms_equipment = self.pool.get('cmms.equipment')
        equipment = cmms_equipment.browse(cr, uid, equipment_id, context=context)
        equipment_part_ids = [p.id for p in equipment.parts_ids]
        return {
                'domain': {
                    'part_id': [('id','in',equipment_part_ids)],
                    'supplier_id': [('id','in',[])],
                    },
                'value': {
                    'part_id': False,
                    'supplier_id': False,
                    },
                }

    def onchange_part(self, cr, uid, ids, equipment_id, part_id, supplier_id, context=None):
        # equipment_id is always known
        product_supplierinfo = self.pool.get('product.supplierinfo')
        equipment_part_ids = [part_id]
        product_suppliers = product_supplierinfo.browse(
                cr, uid,
                [('product_id','in',equipment_part_ids)],
                context=context,
                )
        product_suppliers_ids = [ps.id for ps in product_suppliers]
        supplier_id = part_name = part_code = False
        if len(product_suppliers) == 1:
            [supplier] = product_suppliers
            supplier_id = supplier.id
            part_name = supplier.product_name
            part_code = supplier.product_code
        return {
                'domain': {
                    'supplier_id': [('id','in',product_suppliers_ids)],
                    },
                'value': {
                    'supplier_id': supplier_id,
                    'part_name': part_name,
                    'part_code': part_code
                    },
                }

    def onchange_supplier(self, cr, uid, ids, equipment_id, part_id, supplier_id, context=None):
        product_supplierinfo = self.pool.get('product.supplierinfo')
        product_supplier = product_supplierinfo.browse( cr, uid, supplier_id, context=context)
        return {
                'value': {
                    'part_code': product_supplier.product_code,
                    'part_name': product_supplier.product_name,
                    },
                }

class cmms_archiving3(Normalize, osv.Model):
    "work-order archive"
    _name = "cmms.archiving3"
    _description = "Incident follow-up history"

    _columns = {
        'name': fields.char('Object', size=32, required=True),
        'date': fields.datetime('Date'),
        'description': fields.text('Description'),
        'incident_id': fields.many2one('cmms.incident', 'Incident',required=True, ondelete='cascade'),
        'user_id': fields.many2one('res.users', 'Assigned to'),
        }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda object,cr,uid,context: uid,
        }


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
        'user_id': fields.many2one('res.users', 'Sender', domain=[('groups_id','=',fields.ref('cmms.group_cmms_staff'))]),
        'user2_id': fields.many2one('res.users', 'Recipient', domain=[('groups_id','=',fields.ref('cmms.group_cmms_staff'))]),
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
            vals['ref_num'] = self.pool.get('ir.sequence').next_by_code(cr, user, 'cmms.intervention', context=context)
        machines = self.pool.get('cmms.equipment')
        machine = machines.browse(cr, 1, vals['equipment_id'], context=context)
        vals['name'] = (
                "%s - %s - %s - %s"
                % (
                    vals['ref_num'],
                    vals['type'],
                    machine.name.strip(),
                    vals['description'] or '')
                ).strip(' -')
        return super(cmms_intervention, self).create(cr, user, vals, context)


# Checklists
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
        question_ids = self.pool.get('cmms.question').search(cr, uid, [('checklist_id', '=', id)], context=context)
        records = self.pool.get('cmms.question').name_get(cr, uid, question_ids, context=context)
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
        'user_id': fields.many2one('res.users', 'Assigned to', domain=[('groups_id','=',fields.ref('cmms.group_cmms_staff'))]),
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

# product.product enhancements
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
        'equipment_ids': fields.many2many(
            'cmms.equipment',
            'product_equipment_rel',
            'product_id',
            'equipment_id',
            string=' Used in',
            ),
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


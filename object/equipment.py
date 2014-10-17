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

from fnx import Normalize
from osv import osv, fields
import pooler
import math
from tools import config
from tools.translate import _
import time

class cmms_line(Normalize, osv.osv):
    _name = 'cmms.line'
    _description = 'Production line'

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
cmms_line()

class cmms_equipment(Normalize, osv.osv):
    _name = "cmms.equipment"
    _description = "equipment"
    
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

    _columns = {
        'name': fields.char('Machine', size=64, required=True),
        'inv_tag': fields.char('Inventory ID', size=64),
        'trademark': fields.char('Make', size=64),
        'model': fields.char('Model', size=64),
        # 'local_id': fields.many2one('stock.location', 'Location'),
        'line_id': fields.many2one('cmms.line','Production Line', required=True, change_default=True),
        'invoice_id': fields.many2one('account.invoice', 'Purchase Invoice'),
        'startingdate': fields.datetime("Start Date"),
        'product_ids': fields.many2many('product.product','product_equipment_rel','product_id','equipment_id','Spare Parts',
                                        domain="[('product_tmpl_id.categ_id.name','=','Spare Parts')]",),
        'deadlinegar': fields.datetime("Warranty Expiration"),
        'description': fields.text('Description'),
        'safety': fields.text('Safety Instruction'),
        'user_id': fields.many2one(
                'res.users',
                'Assigned to',
                domain="[('groups_id.category_id.name','=','CMMS')]",
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
cmms_equipment()

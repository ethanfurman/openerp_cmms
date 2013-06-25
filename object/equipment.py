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

from osv import osv, fields
import pooler
import math
from tools import config
from tools.translate import _
import time
import mx.DateTime
from mx.DateTime import RelativeDateTime, today, DateTime, localtime

class cmms_line(osv.osv):
    _name = 'cmms.line'
    _description = 'Production line'
    _columns = {
        'name': fields.char('Production line', size=64, required=True),
        'code': fields.char('Reference', size=64),
        'location': fields.char('Location', size=64),
        'sequence': fields.integer('Sequence'),
    }
    def create(self, cr, user, vals, context=None):
        if ('code' not in vals) or (vals.get('code')==''):
            vals['code'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.line')
        return super(cmms_line, self).create(cr, user, vals, context)
    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if default is None:
            default = {}
        default = default.copy()
        default['code'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.line')
        return super(cmms_line, self).copy(cr, uid, id, default=default, context=context)
cmms_line()

class cmms_equipment(osv.osv):
    _name = "cmms.equipment"
    _description = "equipment"
    def create(self, cr, user, vals, context=None):
        if ('type' not in vals) or (vals.get('type')==''):
            vals['type'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.equipment')
        return super(cmms_equipment, self).create(cr, user, vals, context)
    _columns = {
        'type': fields.char('Reference', size=64),
        'name': fields.char('Name', size=64 , required=True),
        'trademark': fields.char('Brand', size=64),
        'active' : fields.boolean('Active'),
        'local_id': fields.many2one('stock.location', 'Location'),
        'line_id': fields.many2one('cmms.line','Production Line', required=True, change_default=True),
        'invoice_id': fields.many2one('account.invoice', 'Purchase Invoice'),
        'startingdate': fields.datetime("Start Date"),
        'product_ids': fields.many2many('product.product','product_equipment_rel','product_id','equipment_id','Spare Parts'),
        'deadlinegar': fields.datetime("Warranty Expiration"),
        'description': fields.text('Description'),
        'safety': fields.text('Safety Instruction'),
        'user_id': fields.many2one('res.users', 'Assigned to'),
    }
    _defaults = {
        'active' : lambda *a: True,
        'user_id': lambda object,cr,uid,context: uid,
    }
    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if default is None:
            default = {}
        default = default.copy()
        default['type'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.equipment')
        return super(cmms_equipment, self).copy(cr, uid, id, default=default, context=context)
cmms_equipment()

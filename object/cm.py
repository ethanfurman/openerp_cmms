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

import pooler
import math
import time
import mx.DateTime
from oe_utils import Normalize
from tools import config
from tools.translate import _
from osv import osv, fields
from mx.DateTime import RelativeDateTime, today, DateTime, localtime

class cmms_failure(Normalize, osv.osv):
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
cmms_failure()

class cmms_cm(Normalize, osv.osv):
    _name = "cmms.cm"
    _description = "Corrective Maintenance System"

    def create(self, cr, uid, vals, context=None):
        if 'reference' not in vals or not vals['reference']:
            vals['reference'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.cm')
        return super(cmms_cm, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['reference'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.cm')
        return super(cmms_cm, self).copy(cr, uid, id, default=default, context=context)

    _columns = {
        'reference': fields.char('CM Reference',size=20),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'failure_id': fields.many2one('cmms.failure', 'Failure?'),
        'date': fields.datetime('Date'),
        'note': fields.text('Notes'),
        'user_id': fields.many2one('res.users', 'Responsible', domain="[('groups_id.category_id.name','=','CMMS')]"),
        'diagnosistab_ids': fields.one2many('cmms.diagnosistab', 'cm_id', 'Diagnostic Table'),
        'archiving_ids': fields.one2many('cmms.archiving', 'cm_id', 'Follow-up History'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda object,cr,uid,context: uid,
    }
    _sql_constraints = [
            ('cm_ref_key', 'unique(reference)', 'CM Reference already exists'),
            ]
    _constraints = [
            (lambda s, *a: s.check_unique('reference', *a), '\nCM Reference already exists', ['reference']),
            ]
cmms_cm()

class cmms_diagnosistab(Normalize, osv.osv):
    _name = "cmms.diagnosistab"
    _description = "Diagnostics List"
    _columns = {
        'name': fields.char('Failure Causes', size=32, required=True),
        'solution': fields.text('Solution'),
        'cm_id': fields.many2one('cmms.cm', 'Corrective Maintenance'),
    }
cmms_diagnosistab()

class cmms_archiving(Normalize, osv.osv):
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
cmms_archiving()

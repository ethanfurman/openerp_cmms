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
import datetime
from dateutil.relativedelta import *
import time
from tools import config
from tools.translate import _
import mx.DateTime
from mx.DateTime import RelativeDateTime, today, DateTime, localtime

class cmms_pm(osv.osv):
    _name = "cmms.pm"
    _description = "Preventive Maintenance System"
    
    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context):
        res = self.name_get(cr, uid, ids, context)
        return dict(res)
    
    def _days_next_due(self, cr, uid, ids, prop, unknow_none, context):
        if ids:
            reads = self.browse(cr, uid, ids, context)
            res = []
            for record in reads:
                if (record.meter == "days"):
                    interval = datetime.timedelta(days=record.days_interval)
                    last_done = record.days_last_done
                    last_done = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_done, "%Y-%m-%d")))
                    next_due = last_done + interval
                    res.append((record.id, next_due.strftime("%Y-%m-%d")))
                else:
                    res.append((record.id, False))
            return dict(res)
    
    def _days_due(self, cr, uid, ids, prop, unknow_none, context):
        if ids:
            reads = self.browse(cr, uid, ids, context)
            res = []
            for record in reads:
                if (record.meter == "days"):
                    interval = datetime.timedelta(days=record.days_interval)
                    last_done = record.days_last_done
                    last_done = datetime.datetime.fromtimestamp(time.mktime(time.strptime(last_done, "%Y-%m-%d")))
                    next_due = last_done + interval
                    NOW = datetime.datetime.now()
                    due_days = next_due - NOW
                    res.append((record.id, due_days.days))
                else:
                    res.append((record.id, False))
            return dict(res)

    def _get_state(self, cr, uid, ids, prop, unknow_none, context):
        res = {}
        if ids:
            reads = self.browse(cr, uid, ids, context)
            for record in reads:    
                if record.meter == 'days':
                    if (int(record.days_left) <= 0):
                        res[record.id] = _('Overdue')
                    elif (int(record.days_left) <= record.days_warn_period):
                        res[record.id] = _('Approaching')
                    else:
                        res[record.id] = 'OK'
            return res

    def create(self, cr, user, vals, context=None):
        if ('name' not in vals) or (vals.get('name')==''):
            vals['name'] = self.pool.get('ir.sequence').get(cr, user, 'cmms.pm')
        return super(cmms_pm, self).create(cr, user, vals, context)
    
    _columns = {
        'name':fields.char('PM Reference',size=20, required=True),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine', required=True),
        'meter':fields.selection([ ('days', 'Days')], 'Unit of measure'),
        'recurrent':fields.boolean('Recurrent ?', help="Mark this option if PM is periodic"),
        'days_interval':fields.integer('Interval'),
        'days_last_done':fields.date('Last done',required=True),
        'days_next_due':fields.function(_days_next_due, method=True, type="date", string='Next service date'),
        'days_warn_period':fields.integer('Warning time'),
        'days_left':fields.function(_days_due, method=True, type="integer", string='Days until next service'),
        'state':fields.function(_get_state, method=True, type="char", string='Status')
    }
    _defaults = {
        'meter': lambda * a: 'days',
        'recurrent': lambda * a: True,
        'days_last_done': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if default is None:
            default = {}
            default = default.copy()
            default['name'] = self.pool.get('ir.sequence').get(cr, uid, 'cmms.pm')
        return super(cmms_pm, self).copy(cr, uid, id, default=default, context=context)
cmms_pm()

class cmms_archiving2(osv.osv):
    _name = "cmms.archiving2"
    _description = "PM follow-up history"
    _columns = {
        'name': fields.char('effect', size=32, required=True),
        'date': fields.datetime('Date'),
        'description': fields.text('Description'),
        'pm_id': fields.many2one('cmms.pm', 'Archiving',required=True),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

cmms_archiving2()

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

from oe_utils import Normalize
from osv import fields,osv
from osv import orm
from tools.translate import _

YESNO = [
    ('yes','Yes'),
    ('no','No'),
    ]

STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('done', 'Done'),
    ]

class cmms_checklist(Normalize, osv.Model):
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
cmms_checklist()

class cmms_question(Normalize, osv.Model):
    _name = "cmms.question"
    _description = "Question"
    _columns = {
        'name': fields.char("Question",size=128, required=True),
        'checklist_id': fields.many2one('cmms.checklist', 'Checklist', required=True), 
    }
cmms_question()

class cmms_checklist_history(Normalize, osv.Model):
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
        'user_id': fields.many2one('res.users', 'Assigned to'),
        'status': fields.selection(STATES, "Status"),
        }
    _defaults = {
        'status' : lambda *a: 'draft',
        'user_id': lambda object,cr,uid,context: uid,
    }
cmms_checklist_history()

class cmms_question_history(Normalize, osv.Model):
    _name="cmms.answer.history"
    _description= "Answers"
    _columns={    
        'name': fields.char("Question",size=128, required=True),
        'checklist_history_id': fields.many2one('cmms.checklist.history', 'Checklist'),
        'answer': fields.selection(YESNO, "Response"),
        'detail': fields.char("Detail",size=128),
    }
cmms_question_history()

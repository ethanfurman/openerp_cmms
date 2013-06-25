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

from osv import fields,osv
from osv import orm
from tools.translate import _

CHOICE = [
    ('yes','Yes'),
    ('no','No'),
]

class cmms_checklist(osv.osv):
    _name="cmms.checklist"
    _description= "checklist"
    _columns={
        'name': fields.char("Title",size=128, required=True),
        'description': fields.text('Description'), 
        'questions_ids': fields.one2many("cmms.question","checklist_id","Questions",),
        'equipment_id': fields.many2one('cmms.equipment', 'Machine'),
        }
cmms_checklist()

class cmms_question(osv.osv):
    _name = "cmms.question"
    _description = "Question"
    _columns = {
        'name': fields.char("Question",size=128, required=True),
        'checklist_id': fields.many2one('cmms.checklist', 'Checklist', required=True), 
    }
cmms_question()

class cmms_checklist_history(osv.osv):
    _name="cmms.checklist.history"
    _description= "Checklist History"
    
    def onchange_checklist_id(self, cr, uid, ids, id, context={}):
        liste = self.pool.get('cmms.question').search(cr, uid, [('checklist_id', '=', id)])
        enrs = self.pool.get('cmms.question').name_get(cr, uid, liste)
        res = []
        for id, name in enrs:
            obj = {'name': name}
            res.append(obj)
        return {'value':{'answers_ids': res}}
    
    def create(self, cr, uid, vals, context=None):
        for i, obj in enumerate(vals['answers_ids']):
            vals['answers_ids'][i] = [0,0,vals['answers_ids'][i][2]]
        return osv.osv.create(self, cr, uid, vals, context=context)
    
    _columns={
        'name': fields.char("Name",size=128, required=True),
        'checklist_id': fields.many2one('cmms.checklist', 'Checklist'), 
        'answers_ids': fields.one2many("cmms.answer.history","checklist_history_id","Responses"),
        'date_planned': fields.datetime("Planned Date"), 
        'date_end': fields.datetime("Completed Date"), 
        'equipment_id': fields.many2one('cmms.equipment', 'Machine'),
        'user_id': fields.many2one('res.users', 'Assigned to'),
        'status': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),('done', 'Done')], "Status"),
        }
    _defaults = {
        'status' : lambda *a: 'draft',
        'user_id': lambda object,cr,uid,context: uid,
    }
    
cmms_checklist_history()

class cmms_question_history(osv.osv):
    _name="cmms.answer.history"
    _description= "Answers"
    _columns={    
        'name': fields.char("Question",size=128, required=True),
        'checklist_history_id': fields.many2one('cmms.checklist.history', 'Checklist'),
        'answer': fields.selection(CHOICE, "Response"),
        'detail': fields.char("Detail",size=128),
    }
    
cmms_question_history()

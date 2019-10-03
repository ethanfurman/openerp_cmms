# -*- coding: utf-8 -*-
################################################################################
#
# Computerized maintenance management system (CMMS) module,
# Copyright (C)
#    Nextma (http://www.nextma.com). All Rights Reserved
#    2005 - 2011 Héonium (http://heonium.com). All Rights Reserved
#    2013 Emile van Sebille.  All Rights Reserved.
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
{
    "name": "Computerized Maintenance Management System",
    "version": "2.0",
    "author": "Héonium / Nextma / Emile van Sebille",
    'website': 'http://heonium.com - http://www.nextma.com - http://salesinq.com',
    "category": "Specific Modules/CMMS",
    "description": """
Computerized maintenance management system module allows you to manage
preventive maintenance and repairs without limit.
All information is linked to the equipment tree and lets you follow
maintenance operations:

 - Scheduled Maintenance
 - Repairs
 - Checkists
 - Work Orders
 - ...

With this module you can track all equipment types.
""",
    'depends': [
        'base',
        'fnx',
        'fnx_fs',
        'product',
        ],
    'data': [
        'security/cmms_security.xaml',
        'security/ir.model.access.csv',
        'cmms_view.xaml',
        'cmms_work_order_source.xaml',
        'cmms_sequence.xaml',
        ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

# Copyright 2012 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Copyright 2012 Nebula, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import unicode_literals

from django.db import models
from datetime import datetime

class Project(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(unique=True, max_length=255)
    os_id = models.CharField(max_length=40)
    start = models.DateTimeField()
    state = models.IntegerField(blank=True, null=True)
    remaining = models.FloatField(blank=True, null=True)
    last_update = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'project'

    def __str__(self):
        return self.name

class User(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=40)
    password = models.CharField(max_length=255, blank=True, null=True)
    idp = models.CharField(max_length=30)
    cn = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField()
    duration = models.IntegerField(blank=True, null=True)
    project = models.ForeignKey(Project, models.DO_NOTHING, db_column='project', blank=True, null=True)
    updated = models.DateTimeField()

    class Meta:
        managed = True
        db_table = 'user'

    def __str__(self):
        return self.name

    @staticmethod
    def update_user(user_data):
        user = User.objects.get(id=int(user_data['id']))
        user.name = user_data['name']
        user.email = user_data['email']
        user.idp = user_data['idp']
        user.cn = user_data['cn']
        user.source = user_data['source']
        if str(user_data['project']) != '':
            user.project = Project.objects.get(id=int(user_data['project']))
        else:
            user.project = None
        user.duration = user_data['duration']
        user.updated = datetime.now()
        user.save()

    @staticmethod
    def create_user(user_data):
        if str(user_data['project']) != '':
            project = Project.objects.get(id=int(user_data['project']))
        else:
            project = None
        new_user = User(
            name=user_data['name'],
            email=user_data['email'],
            idp=user_data['idp'],
            password=user_data['password'],
            cn=user_data['cn'],
            source=user_data['source'],
            project=project,
            duration=user_data['duration'],
            created=datetime.now()
        )
        new_user.save()

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

import collections
import logging

from django.conf import settings
from django.forms import ValidationError
from django import http
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon.utils import functions as utils
from horizon.utils import validators

from openstack_dashboard import api
from openstack_dashboard.dashboards.identity.users.forms \
    import AddExtraColumnMixIn, PasswordMixin
from garr_horizon.content.garr_users.models import User, Project
from openstack_dashboard.local.local_settings import KEYSTONE_USER_PASS

LOG = logging.getLogger(__name__)
PROJECT_REQUIRED = api.keystone.VERSIONS.active < 3

class BaseUserForm(forms.SelfHandlingForm):
    def __init__(self, request, *args, **kwargs):
        super(BaseUserForm, self).__init__(request, *args, **kwargs)

        # Populate project choices
        user_id = kwargs['initial'].get('id', None)
        default_project_id = kwargs['initial'].get('project', None)
        if default_project_id: default_project_id = default_project_id.id
        project_choices = [(project.id, project.name) for project in Project.objects.all()]
        if not project_choices:
            project_choices.insert(0, ('', _("No available projects")))
        else:
            project_choices.append(('', _('No default project')))
        if default_project_id is None:
            project_choices.insert(0, ('', _('Select a project')))
        self.fields['project'].choices = project_choices



class CreateUserForm(PasswordMixin, BaseUserForm):
    name = forms.CharField(max_length=100, label=_("User Name"))
    email = forms.EmailField(max_length=40, label=_("Email"))
    project = forms.ThemableDynamicChoiceField(label=_("Project"), required=False)
    idp = forms.CharField(max_length=30, label=_("Identity Provider"))
    cn = forms.CharField(max_length=255, label=_("Common Name"), required=False)
    duration = forms.IntegerField(label=_("Duration"), required=False)
    source = forms.CharField(max_length=255, label=_("Source"), required=False) 

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        # Reorder form fields from multiple inheritance
        ordering = ["name", "email", "password", "confirm_password",
                    "project", "idp", "cn", "duration", "source"]
        self.fields = collections.OrderedDict(
            (key, self.fields[key]) for key in ordering)


    # We have to protect the entire "data" dict because it contains the
    # password and confirm_password strings.
    @sensitive_variables('data')
    def handle(self, request, data):
        try:
            LOG.info('Creating GARR user with name "%s"', data['name'])
            new_user = User.create_user(data)
            messages.success(request,
                             _('User "%s" was successfully created.')
                             % data['name'])
            return True
        except Exception:
            messages.error(request , _('Unable to create user.'))
            return exceptions.handle(request, ignore=True)

class UpdateUserForm(BaseUserForm):
    id = forms.CharField(label=_("ID"), widget=forms.HiddenInput)
    name = forms.CharField(max_length=100, label=_("User Name"))
    email = forms.EmailField(max_length=40, label=_("Email"))
    project = forms.ThemableChoiceField(label=_(" Project"), required=False)
    idp = forms.CharField(max_length=30, label=_("Identity Provider"))
    cn = forms.CharField(max_length=255, label=_("Common Name"),required=False)
    source = forms.CharField(max_length=255, label=_("Source"), required=False)
    duration = forms.IntegerField(label=_("Duration"), required=False)

    def __init__(self, request, *args, **kwargs):
        super(UpdateUserForm, self).__init__(request, *args, **kwargs)
        if api.keystone.keystone_can_edit_user() is False:
            for field in ('name', 'email'):
                self.fields.pop(field)

    def handle(self, request, data):
        try:
            User.update_user(data)
            messages.success(request,
                             _('User has been updated successfully.'))
            return True
        except Exception:
            messages.error(request, _('Unable to update the user.'))
            return exceptions.handle(request, ignore=True)

class ActivateUserForm(PasswordMixin, BaseUserForm, AddExtraColumnMixIn):
    # Hide the domain_id and domain_name by default
    domain_id = forms.CharField(label=_("Domain ID"),
                                required=False,
                                widget=forms.HiddenInput())
    domain_name = forms.CharField(label=_("Domain Name"),
                                  required=False,
                                  widget=forms.HiddenInput())
    name = forms.CharField(max_length=255, label=_("User Name"))
    description = forms.CharField(widget=forms.widgets.Textarea(
                                  attrs={'rows': 4}),
                                  label=_("Description"),
                                  required=False)
    email = forms.EmailField(
        label=_("Email"),
        required=False)
    project = forms.ThemableDynamicChoiceField(label=_("Primary Project"),
                                               required=PROJECT_REQUIRED)
    role_id = forms.ThemableChoiceField(label=_("Role"),
                                        required=PROJECT_REQUIRED)
    enabled = forms.BooleanField(label=_("Enabled"),
                                 required=False,
                                 initial=True)

    default_user_id = forms.IntegerField(label=_('User ID'),
                                        widget=forms.HiddenInput())

    @staticmethod
    def get_os_projects(request, project_name, domain_id):
        # Populate project choices
        project_choices = []
        keystone_projects, has_more = api.keystone.tenant_list(request)
        matching_project = None

        # Check if asigned project matches
        # with the ones from Keystone and
        # set that project as a default choice
        for project in keystone_projects:
            if project.enabled:
                if project_name == project.name:
                    matching_project = (project.id, project.name)
                else:
                    project_choices.append((project.id, project.name))

        if matching_project:
            project_choices.append(0, matching_project)
        elif not project_choices:
            project_choices.insert(0, ('', _('No available projects')))
        else:
            project_choices.insert(0, ('', _('Select a project.')))
        return project_choices

    def __init__(self, *args, **kwargs):
        roles = kwargs.pop('roles')
        super(ActivateUserForm, self).__init__(*args, **kwargs)
        project_name = kwargs['initial'].get('project', None)
        domain_id = kwargs['initial'].get('domain_id', None)
        self.fields['project'].choices = self.get_os_projects(args[0], project_name, domain_id)
        # Reorder form fields from multiple inheritance
        ordering = ["default_user_id", "domain_id", "domain_name", "name",
                    "description", "email", "password",
                    "confirm_password", "project", "role_id",
                    "enabled"]
        self.add_extra_fields(ordering)
        self.fields = collections.OrderedDict(
            (key, self.fields[key]) for key in ordering)
        role_choices = [(role.id, role.name) for role in roles]
        self.fields['role_id'].choices = role_choices

        # For keystone V3, display the two fields in read-only
        if api.keystone.VERSIONS.active >= 3:
            readonlyInput = forms.TextInput(attrs={'readonly': 'readonly'})
            self.fields["domain_id"].widget = readonlyInput
            self.fields["domain_name"].widget = readonlyInput
        # For keystone V2.0, hide description field
        else:
            self.fields["description"].widget = forms.HiddenInput()

        # Disable required constraint on password field
        # If no password is inserted the default one is used
        self.fields['password'].required = False
        self.fields['confirm_password'].required = False

    # We have to protect the entire "data" dict because it contains the
    # password and confirm_password strings.
    @sensitive_variables('data')
    def handle(self, request, data):
        user_id = data.get('default_user_id', None)
        if not data['password']:
            data['password'] = KEYSTONE_USER_PASS

        return self.create_keystone_user(request, data)

    @staticmethod
    def create_keystone_user(request, data):
        domain = api.keystone.get_default_domain(request, False)
        try:
            LOG.info('Creating user with name "%s"', data['name'])
            # add extra information
            if api.keystone.VERSIONS.active >= 3:
                EXTRA_INFO = getattr(settings, 'USER_TABLE_EXTRA_INFO', {})
                kwargs = dict((key, data.get(key)) for key in EXTRA_INFO)
            else:
                kwargs = {}
            new_user = \
                api.keystone.user_create(request,
                                         name=data['name'],
                                         email=data['email'],
                                         description=data['description'] or None,
                                         password=data['password'],
                                         project=data['project'] or None,
                                         enabled=data['enabled'],
                                         domain=domain.id,
                                         **kwargs)
            messages.success(request,
                             _('User "%s" was successfully created.')
                             % data['name'])
            if data['project'] and data['role_id']:
                roles = api.keystone.roles_for_user(request,
                                                    new_user.id,
                                                    data['project']) or []
                assigned = [role for role in roles if role.id == str(
                    data['role_id'])]
                if not assigned:
                    try:
                        api.keystone.add_tenant_user_role(request,
                                                          data['project'],
                                                          new_user.id,
                                                          data['role_id'])
                    except Exception:
                        exceptions.handle(request,
                                          _('Unable to add user '
                                            'to primary project.'))
            return new_user
        except exceptions.Conflict:
            msg = _('User name "%s" is already used.') % data['name']
            messages.error(request, msg)
        except Exception:
            exceptions.handle(request, _('Unable to create user.'))


class ChangePasswordForm(PasswordMixin, forms.SelfHandlingForm):
    id = forms.CharField(widget=forms.HiddenInput)
    name = forms.CharField(
        label=_("User Name"),
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False)

    @sensitive_variables('data', 'password')
    def handle(self, request, data):
        user_id = data.pop('id')
        password = data.pop('password')

        # Throw away the password confirmation, we're done with it.
        data.pop('confirm_password', None)

        try:
            user = User.objects.get(id=user_id)
            user.password = User.hash_password(password)
            user.save()
            messages.success(request,
                             _('User password has been updated successfully.'))
            return True
        except Exception:
            messages.error(request, _('Unable to update the user password.'))


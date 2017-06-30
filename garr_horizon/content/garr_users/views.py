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

import logging
import operator

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import tables
from horizon.utils import memoized
from horizon import views

from openstack_dashboard import api
from openstack_dashboard import policy

from garr_horizon.content.garr_users import forms as project_forms
from garr_horizon.content.garr_users import tables as project_tables
from openstack_dashboard.utils import identity
from garr_horizon.content.garr_users.models import User, Project

LOG = logging.getLogger(__name__)

class IndexView(tables.DataTableView):
    table_class = project_tables.UsersTable
    template_name = 'identity/garr_users/index.html'
    page_title = _("External Users")

    def get_filters(self):
        filter_field = self.table.get_filter_field()
        filter_string = self.table.get_filter_string()
        if filter_string:
            if filter_field == 'project':
                filter_string = Project.objects.get(name=filter_string).id
            return {filter_field: filter_string}
        else:
            return None

    def get_data(self):
        users = []
        list_permission = False
        if policy.check((("identity", "identity:list_users"),),
                        self.request):
            list_permission = True
        elif policy.check((("identity", "identity:get_user"),),
                          self.request):
            list_permission = True

        if list_permission:
            filters = self.get_filters()
            try:
                if filters is not None:
                    return User.objects.filter(**filters)
                else:
                    return User.objects.all()
            except Exception:
                exceptions.handle(self.request,
                                    _('Unable to retrieve user list.'))
        else:
            msg = _("Insufficient privilege level to view user information.")
            messages.info(self.request, msg)

class UpdateView(forms.ModalFormView):
    template_name = 'identity/garr_users/update.html'
    form_id = "update_user_form"
    form_class = project_forms.UpdateUserForm
    submit_label = _("Update User")
    submit_url = "horizon:identity:garr_users:update"
    success_url = reverse_lazy('horizon:identity:garr_users:index')
    page_title = _("Update User")

    def dispatch(self, *args, **kwargs):
        return super(UpdateView, self).dispatch(*args, **kwargs)

    @memoized.memoized_method
    def get_object(self):
        try:
            return User.objects.get(id=self.kwargs['user_id'])
        except Exception:
            redirect = reverse("horizon:identity:garr_users:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve user information.'),
                              redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        args = (self.kwargs['user_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        user = self.get_object()
        data = {'id': user.id,
                'name': user.name,
                'project': user.project,
                'email': getattr(user, 'email'),
                'idp': getattr(user, 'idp'),
                'cn': getattr(user, 'cn', ''),
                'source': getattr(user, 'source', ''),
                'duration': getattr(user, 'duration', ''),
               }
        return data


class CreateView(forms.ModalFormView):
    template_name = 'identity/garr_users/create.html'
    form_id = "create_user_form"
    form_class = project_forms.CreateUserForm
    submit_label = _("Create User")
    submit_url = reverse_lazy("horizon:identity:garr_users:create")
    success_url = reverse_lazy('horizon:identity:garr_users:index')
    page_title = _("Create User")

    @method_decorator(sensitive_post_parameters('password',
                                                'confirm_password'))
    def dispatch(self, *args, **kwargs):
        return super(CreateView, self).dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(CreateView, self).get_form_kwargs()
        return kwargs



class DetailView(views.HorizonTemplateView):
    template_name = 'identity/garr_users/detail.html'
    page_title = "{{ user.name }}"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        user = self.get_data()
        table = project_tables.UsersTable(self.request)
        context["user"] = user
        context["url"] = self.get_redirect_url()
        context["actions"] = table.render_row_actions(user)
        return context

    @memoized.memoized_method
    def get_data(self):
        try:
            user_id = self.kwargs['user_id']
            user = User.objects.get(id=user_id)
        except Exception:
            redirect = self.get_redirect_url()
            exceptions.handle(self.request,
                              _('Unable to retrieve user details.'),
                              redirect=redirect)
        return user

    def get_redirect_url(self):
        return reverse('horizon:identity:garr_users:index')


class ChangePasswordView(forms.ModalFormView):
    template_name = 'identity/garr_users/change_password.html'
    form_id = "change_user_password_form"
    form_class = project_forms.ChangePasswordForm
    submit_url = "horizon:identity:garr_users:change_password"
    submit_label = _("Save")
    success_url = reverse_lazy('horizon:identity:garr_users:index')
    page_title = _("Change Password")

    @method_decorator(sensitive_post_parameters('password',
                                                'confirm_password'))
    def dispatch(self, *args, **kwargs):
        return super(ChangePasswordView, self).dispatch(*args, **kwargs)

    @memoized.memoized_method
    def get_object(self):
        try:
            return User.objects.get(id=self.kwargs['user_id'])
        except Exception:
            redirect = reverse("horizon:identity:garr_users:index")
            exceptions.handle(self.request,
                              _('Unable to retrieve user information.'),
                              redirect=redirect)

    def get_context_data(self, **kwargs):
        context = super(ChangePasswordView, self).get_context_data(**kwargs)
        args = (self.kwargs['user_id'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_initial(self):
        user = self.get_object()
        return {'id': self.kwargs['user_id'],
                'name': user.name}

class ActivateView(forms.ModalFormView):
    template_name = 'identity/garr_users/create.html'
    form_id = "activate_user_form"
    form_class = project_forms.ActivateUserForm
    submit_label = _("Activate User")
    submit_url = reverse_lazy("horizon:identity:garr_users:create_keystone")
    success_url = reverse_lazy('horizon:identity:users:index')
    page_title = _("Create Keystone User")

    @method_decorator(sensitive_post_parameters('password',
                                                'confirm_password'))
    def dispatch(self, *args, **kwargs):
        return super(ActivateView, self).dispatch(*args, **kwargs)

    @staticmethod
    @memoized.memoized_method
    def get_object(user_id):
        try:
            return User.objects.get(id=user_id)
        except Exception:
            redirect = reverse('horizon:identity:garr_users:index')
            exceptions.handle(self.request,
                              _('Unable to retrieve user information.'))

    def get_form_kwargs(self):
        kwargs = super(ActivateView, self).get_form_kwargs()
        try:
            roles = api.keystone.role_list(self.request)
        except Exception:
            redirect = reverse("horizon:identity:garr_users:index")
            exceptions.handle(self.request,
                              _("Unable to retrieve user roles."),
                              redirect=redirect)
        roles.sort(key=operator.attrgetter("id"))
        kwargs['roles'] = roles
        return kwargs

    def get_initial(self):
        # Set the domain of the user
        domain = api.keystone.get_default_domain(self.request)
        default_role = api.keystone.get_default_role(self.request)
        user_id = self.kwargs.get('user_id', None)
        if not user_id:
            return  {
                'domain_id': domain.id,
                'domain_name': domain.name,
                'role_id': getattr(default_role, "id", None)
            }
        else:
            user = self.get_object(user_id)
            return {'domain_id': domain.id,
                    'domain_name': domain.name,
                    'role_id': getattr(default_role, "id", None),
                    'name': user.name,
                    'email': user.email,
                    'default_user_id': int(user.id)}


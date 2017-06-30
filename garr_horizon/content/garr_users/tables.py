# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from django.template import defaultfilters
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import forms
from horizon import tables
from openstack_dashboard import api
from openstack_dashboard import policy

from garr_horizon.content.garr_users.models import User
from garr_horizon.content.garr_users.forms import ActivateUserForm
from openstack_dashboard.local.local_settings import KEYSTONE_USER_PASS

class ActivateUserLink(tables.LinkAction):
    name = "activate"
    verbose_name = _("Custom Keystone Create")
    url = "horizon:identity:garr_users:activate"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (('identity', 'identity:create_grant'),
                    ("identity", "identity:create_user"),
                    ("identity", "identity:list_roles"),
                    ("identity", "identity:list_projects"),)

    def allowed(self, request, user):
        return api.keystone.keystone_can_edit_user()


class CreateUserLink(tables.LinkAction):
    name = "create"
    verbose_name = _("Create User")
    url = "horizon:identity:garr_users:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (('identity', 'identity:create_grant'),
                    ("identity", "identity:create_user"),
                    ("identity", "identity:list_roles"),
                    ("identity", "identity:list_projects"),)

    def allowed(self, request, user):
        return api.keystone.keystone_can_edit_user()


class EditUserLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit")
    url = "horizon:identity:garr_users:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("identity", "identity:update_user"),
                    ("identity", "identity:list_projects"),)
    policy_target_attrs = (("user_id", "id"),
                           ("target.user.domain_id", "domain_id"),)


    def allowed(self, request, user):
        return api.keystone.keystone_can_edit_user()


class ChangePasswordLink(policy.PolicyTargetMixin, tables.LinkAction):
    name = "change_password"
    verbose_name = _("Change Password")
    url = "horizon:identity:garr_users:change_password"
    classes = ("ajax-modal",)
    icon = "key"
    policy_rules = (("identity", "identity:change_password"),)
    policy_target_attrs = (("user_id", "id"),)

    def allowed(self, request, user):
        return api.keystone.keystone_can_edit_user()

class DeleteUsersAction(policy.PolicyTargetMixin, tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete User",
            u"Delete Users",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted User",
            u"Deleted Users",
            count
        )
    policy_rules = (("identity", "identity:delete_user"),)

    def allowed(self, request, datum):
        if not api.keystone.keystone_can_edit_user() or \
                (datum and datum.id == request.user.id):
            return False
        return True

    def delete(self, request, obj_id):
        User.objects.filter(id=obj_id).delete()

class EnableUsersAction(tables.BatchAction):
    policy_rules = (('identity', 'identity:create_grant'),
                    ("identity", "identity:create_user"),
                    ("identity", "identity:list_roles"),
                    ("identity", "identity:list_projects"),)

    name = "enable"
    icon = "plus"
    success_url = "horizon:identity:garr_users:index"

    def action(self, request, user_id):
        self.enable(request, user_id)

    def allowed(self, request, user):
        return api.keystone.keystone_can_edit_user()

    def enable(self, request, user_id):
        pdb.set_trace()
        domain = api.keystone.get_default_domain(request)
        default_role = api.keystone.get_default_role(request)
        keystone_projects, has_more = api.keystone.tenant_list(request)
        try:
            user_obj = User.objects.get(id=user_id)
        except Exception:
            msg = _('Unable to find user with the following id - %d' % user_id)
            messages.error(request, msg)

        default_project = None
        if user_obj.project:
            for project in keystone_projects:
                if user_obj.project == project.name:
                    default_project = project.name
        user_data = {
            'name': user_obj.name,
            'email': user_obj.email,
            'description': '',
            'password': KEYSTONE_USER_PASS,
            'project': default_project,
            'enabled': True
        }

        keystone_user = ActivateUserForm.create_keystone_user(request, user_data)
        if not keystone_user:
            msg = _('Unable to create user, %s, in keystone' % user_obj.name)
            messages.error(request, msg)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Keystone Create",
            u"Create Keystone Users",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Keystone Create",
            u"Create Keystone Users",
            count
        )

class UserFilterAction(tables.FilterAction):
    filter_type = "server"
    filter_choices = (("name", _("User Name"), True),
                      ("id", _("User ID"), True),
                      ("idp", _("Identity Provider"), True),
                      ("cn", _("Common Name"), True),
                      ("source", _("Source"), True),
                      ("duration", _("Duration"), True),
                      ("project", _("User Project"), True))


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, user_id):
        return User.objects.filter(id=user_id)


class UsersTable(tables.DataTable):
    STATUS_CHOICES = (
        ("true", True),
        ("false", False)
    )
    name = tables.WrappingColumn('name',
                                 link="horizon:identity:garr_users:detail",
                                 verbose_name=_('User Name'),
                                 form_field=forms.CharField(required=False))
    email = tables.Column(lambda obj: getattr(obj, 'email', None),
                          verbose_name=_('Email'),
                          form_field=forms.EmailField(required=False),
                          filters=(lambda v: defaultfilters
                                   .default_if_none(v, ""),
                                   defaultfilters.escape,
                                   defaultfilters.urlize)
                          )
    id = tables.Column('id', verbose_name=_('User ID'),
                       attrs={'data-type': 'uuid'})

    idp = tables.Column(lambda obj: getattr(obj, 'idp', None),
                          verbose_name=_('Identity Provider'),
                          form_field=forms.CharField(required=False))

    project = tables.Column(lambda obj: str(getattr(obj, 'project', '-')),
                            verbose_name=_('Project'),
                            form_field=forms.CharField(required=False))

    cn = tables.Column(lambda obj: getattr(obj, 'cn', None),
                          verbose_name=_('Common Name'),
                          form_field=forms.CharField(required=True))

    source = tables.Column(lambda obj: getattr(obj, 'source', None),
                          verbose_name=_('Source'),
                          form_field=forms.CharField(required=True))

    duration = tables.Column(lambda obj: getattr(obj, 'duration', None),
                          verbose_name=_('Duration'),
                          form_field=forms.IntegerField(required=True))
    class Meta(object):
        name = "users"
        verbose_name = _("Users")
        row_actions = (EnableUsersAction, ActivateUserLink, EditUserLink, ChangePasswordLink, DeleteUsersAction)
        table_actions = (UserFilterAction, EnableUsersAction, CreateUserLink, DeleteUsersAction)
        row_class = UpdateRow


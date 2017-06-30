from django.utils.translation import ugettext_lazy as _

import horizon

from openstack_dashboard.dashboards.identity import dashboard
from openstack_dashboard.api import keystone


class GarrUsers(horizon.Panel):
    name = _("External Users")
    slug = "garr_users"
    policy_rules = (("identity", "identity:get_user"),
                    ("identity", "identity:list_users"))


    def can_access(self, context):
        if keystone.is_multi_domain_enabled() \
                and not keystone.is_domain_admin(context['request']):
            return False
        return super(GarrUsers, self).can_access(context)

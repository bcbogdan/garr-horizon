# The slug of the panel to be added to HORIZON_CONFIG. Required.
PANEL = 'garr_users'
# The slug of the dashboard the PANEL associated with. Required.
PANEL_DASHBOARD = 'identity'
# The slug of the panel group the PANEL is associated with.
PANEL_GROUP = 'default'
# A list o applications to be prepended to INSTALLED_APPS
ADD_INSTALLED_APPS = ['garr-horizon']
# Python panel class of the PANEL to be added.
ADD_PANEL = 'garr_horizon.content.garr_users.panel.GarrUsers'

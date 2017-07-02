OpenStack Dashboard plugin for Consortium GARR
==============================================

Horizon plugin that provides extra functionality for 
the Consortium GARR cloud.

Installation
----------------------------------

  1. Use pip to install the package on the server running Horizon. 
  2. Copy or link the files in ``garr_horizon/enabled`` to ``openstack_dashboard/local/enabled``. 
     This step will cause the Horizon service to pick up the garr plugin when it starts.
  3. Add extra settings variables to ``local_settings.py``: ``DATABASES``, ``HASHING_ALGORITHM``, 
     ``KEYSTONE_USER_PASS``. Check *Features* for more details.

Features
-------------------------

**User CRUD**

The plugin brovides CRUD operations on GARR users, using the same UI, 
as the ones for Keystone users.

The following variables need to be added to ``local_settings.py`` in order to enable the functionality:

.. code-block::

     # Database settings
     DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': 'db_name',
                'USER': 'db_user',
                'PASSWORD': 'db_pass',
                'HOST': 'db_host',
            }
     }

     # Hashing algorithm to be used for saving passwords
     HASHING_ALGORITHM = 'default' 

For the ``HASHING_ALGORITHM`` the following values can be used: ``pbkdf2_sha256``, ``pbkdf2_sha1``, ``sha1``, ``md5``.

**Keystone User Creation**

GARR Users can be automatically created in Keystone by using the
`Create Keystone User` action or by customizing some of the fields,
when using `Create Custom Keystone User` action.

``KEYSTONE_USER_PASS='default_pass_value'`` needs to be appended to the
``local_settings.py`` file in order to have a predefined default
password when new users are enabled in Keystone.




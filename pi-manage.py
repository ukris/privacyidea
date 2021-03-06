#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 2015-03-27 Cornelius Kölbel, cornelius@privacyidea.org
#            Add sub command for policies
# 2014-12-15 Cornelius Kölbel, info@privacyidea.org
#            Initial creation
#
# (c) Cornelius Kölbel
# Info: http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ./manage.py db init
# ./manage.py db migrate
# ./manage.py createdb
#
import os
import sys
import datetime
import re
from subprocess import call, Popen
from getpass import getpass
from privacyidea.lib.security.default import DefaultSecurityModule
from privacyidea.lib.auth import (create_db_admin, list_db_admin,
                                  delete_db_admin)
from privacyidea.lib.policy import (delete_policy, enable_policy,
                                    PolicyClass, set_policy)
from privacyidea.app import create_app
from flask.ext.script import Manager
from privacyidea.app import db
from flask.ext.migrate import MigrateCommand
# Wee need to import something, so that the models will be created.
from privacyidea.models import Admin
from Crypto.PublicKey import RSA

app = create_app(config_name='production')
manager = Manager(app)
admin_manager = Manager(usage='Create new administrators or modify existing '
                              'ones.')
backup_manager = Manager(usage='Create database backup and restore')
realm_manager = Manager(usage='Create new realms')
resolver_manager = Manager(usage='Create new resolver')
policy_manager = Manager(usage='Manage policies')
manager.add_command('db', MigrateCommand)
manager.add_command('admin', admin_manager)
manager.add_command('backup', backup_manager)
manager.add_command('realm', realm_manager)
manager.add_command('resolver', resolver_manager)
manager.add_command('policy', policy_manager)


@admin_manager.command
def add(username, email, password=None):
    """
    Register a new administrator in the database.
    """
    db.create_all()
    if not password:
        password = getpass()
        password2 = getpass(prompt='Confirm: ')
        if password != password2:
            import sys
            sys.exit('Error: passwords do not match.')

    create_db_admin(app, username, email, password)
    print('Admin {0} was registered successfully.'.format(username))

@admin_manager.command
def list():
    """
    List all administrators.
    """
    list_db_admin()

@admin_manager.command
def delete(username):
    """
    Delete an existing administrator.
    """
    delete_db_admin(username)

@admin_manager.command
def change(username, email=None, password_prompt=False):
    """
    Change the email address or the password of an existing administrator.
    """
    if password_prompt:
        password = getpass()
        password2 = getpass(prompt='Confirm: ')
        if password != password2:
            import sys
            sys.exit('Error: passwords do not match.')
    else:
        password = None

    create_db_admin(app, username, email, password)

@backup_manager.command
def create(directory="/var/lib/privacyidea/backup/"):
    """
    Create a new backup of the database and the configuration. This does not
    backup the encryption key!
    """
    CONF_DIR = "/etc/privacyidea/"
    # INIFILE = "%s/pi.cfg" % CONF_DIR
    DATE = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    BASE_NAME = "privacyidea-backup"
    sqlfile = "%s/dbdump-%s.sql" % (directory, DATE)
    backup_file = "%s/%s-%s.tgz" % (directory, BASE_NAME, DATE)

    sqluri = app.config.get("SQLALCHEMY_DATABASE_URI")
    sqltype = sqluri.split(":")[0]
    if sqltype == "sqlite":
        productive_file = sqluri[len("sqlite:///"):]
        print "Backup SQLite %s" % productive_file
        sqlfile = "%s/db-%s.sqlite" % (directory, DATE)
        call(["cp", productive_file, sqlfile])
    elif sqltype == "mysql":
        m = re.match("mysql://(.*):(.*)@(.*)/(.*)", sqluri)
        username = m.groups()[0]
        password = m.groups()[1]
        datahost = m.groups()[2]
        database = m.groups()[3]
        call("mysqldump -u %s --password=%s -h %s %s > %s" % (username,
                                                              password,
                                                              datahost,
                                                              database,
                                                              sqlfile),
             shell=True)

    else:
        print "unsupported SQL syntax: %s" % sqltype
        sys.exit(2)

    call(["mkdir", "-p", directory])
    call(["tar", "-zcf", backup_file, CONF_DIR, sqlfile])
    os.unlink(sqlfile)
    os.chmod(backup_file, 0600)

@backup_manager.command
def restore(backup_file):
    """
    Restore a previously made backup. You need to specify the tgz file.
    """
    SQLALCHEMY_DATABASE_URI = None
    directory = os.path.dirname(backup_file)
    call(["tar", "-zxf", backup_file, "-C", "/"])
    print 60*"="
    """
    The restore of the SQL file will not work, since at the moment we "
    can not be sure to know the correct SQLALCHEMY_DATABASE_URI. The "
    right URI "
    was just restored to /etc/privacyidea/pi.cfg. So please take a "
    look into that file and restore the SQL dumb from the file "
    /var/lib/privacyidea/backup/*.[sql,sqlite]")
    """
    execfile("/etc/privacyidea/pi.cfg")
    # Now we know the variable SQLALCHEMY_DATABASE_URI
    sqluri = SQLALCHEMY_DATABASE_URI
    if sqluri is None:
        print "No SQLALCHEMY_DATABASE_URI found in /etc/privacyidea/pi.cfg"
        sys.exit(2)
    sqltype = sqluri.split(":")[0]
    if sqltype == "sqlite":
        productive_file = sqluri[len("sqlite:///"):]
        print "Restore SQLite %s" % productive_file
        sqlfile = "%s/db-*.sqlite" % (directory)
        call(["cp", sqlfile, productive_file])
        os.unlink(sqlfile)
    elif sqltype == "mysql":
        m = re.match("mysql://(.*):(.*)@(.*)/(.*)", sqluri)
        username = m.groups()[0]
        password = m.groups()[1]
        datahost = m.groups()[2]
        database = m.groups()[3]
        sqlfile = "%s/dbdump-*.sql" % (directory)
        call("mysql -u %s --password=%s -h %s %s < %s" % (username,
                                                          password,
                                                          datahost,
                                                          database,
                                                          sqlfile), shell=True)
        os.unlink(sqlfile)
    else:
        print "unsupported SQL syntax: %s" % sqltype
        sys.exit(2)


@manager.command
def test():
    """
    Run all nosetests.
    """
    call(['nosetests', '-v',
          '--with-coverage', '--cover-package=privacyidea', '--cover-branches',
          '--cover-erase', '--cover-html', '--cover-html-dir=cover'])

@manager.command
def encrypt_enckey(encfile):
    """
    You will be asked for a password and the encryption key in the specified
    file will be encrypted with an AES key derived from your password.

    The encryption key in the file is a 96 bit binary key.

    The password based encrypted encryption key is a hex combination of an IV
    and the encrypted data.

    The result can be piped to a new enckey file.
    """
    password = getpass()
    password2 = getpass(prompt='Confirm: ')
    if password != password2:
        import sys
        sys.exit('Error: passwords do not match.')
    f = open(encfile)
    enckey = f.read()
    f.close()
    res = DefaultSecurityModule.password_encrypt(enckey, password)
    print res


@manager.command
def create_enckey():
    """
    If the key of the given configuration does not exist, it will be created
    """
    print
    filename = app.config.get("PI_ENCFILE")
    if os.path.isfile(filename):
        print("The file \n\t%s\nalready exist. We do not overwrite it!" %
              filename)
        sys.exit(1)
    f = open(filename, "w")
    f.write(DefaultSecurityModule.random(96))
    f.close()
    print "Encryption key written to %s" % filename
    print "Please ensure to set the access rights for the correct user to 400!"


@manager.command
def create_audit_keys(keysize=2048):
    """
    Create the RSA signing keys for the audit log.
    You may specify an additional keysize.
    The default keysize is 2048 bit.
    """
    filename = app.config.get("PI_AUDIT_KEY_PRIVATE")
    if os.path.isfile(filename):
        print("The file \n\t%s\nalready exist. We do not overwrite it!" %
              filename)
        sys.exit(1)
    new_key = RSA.generate(keysize, e=65537)
    public_key = new_key.publickey().exportKey("PEM")
    private_key = new_key.exportKey("PEM")
    f = open(filename, "w")
    f.write(private_key)
    f.close()

    f = open(app.config.get("PI_AUDIT_KEY_PUBLIC"), "w")
    f.write(public_key)
    f.close()
    print("Signing keys written to %s and %s" %
          (filename, app.config.get("PI_AUDIT_KEY_PUBLIC")))
    print("Please ensure to set the access rights for the correct user to 400!")


@manager.command
def createdb():
    """
    Initially create the tables in the database. The database must exist.
    (SQLite database will be created)
    """
    print db
    db.create_all()
    db.session.commit()


@resolver_manager.command
def create(name, rtype, filename):
    """
    Create a new resolver with name and type (ldapresolver, sqlresolver).
    Read the necessary resolver parameters from the filename. The file should
    contain a python dictionary.

    :param name: The name of the resolver
    :param rtype: The type of the resolver like ldapresolver or sqlresolver
    :param filename: The name of the config file.
    :return:
    """
    from privacyidea.lib.resolver import save_resolver
    import ast

    f = open(filename, 'r')
    contents = f.read()
    f.close()
    params = ast.literal_eval(contents)
    params["resolver"] = name
    params["type"] = rtype
    save_resolver(params)


@resolver_manager.command
def list():
    """
    list the available resolvers and the type
    """
    from privacyidea.lib.resolver import get_resolver_list
    resolver_list = get_resolver_list()
    for name, resolver in resolver_list.iteritems():
        print "%16s - (%s)" % (name, resolver.get("type"))


@realm_manager.command
def list():
    """
    list the available realms
    """
    from privacyidea.lib.realm import get_realms
    realm_list = get_realms()
    for name, realm_data in realm_list.iteritems():
        resolvernames = [x.get("name") for x in realm_data.get("resolver")]
        print "%16s: %s" % (name, resolvernames)


@realm_manager.command
def create(name, resolver):
    """
    Create a new realm.
    This will create a new realm with the given resolver.
    *restriction*: The new realm will only contain one resolver!

    :return:
    """
    from privacyidea.lib.realm import set_realm
    set_realm(name, [resolver])


# Policy interface

@policy_manager.command
def list():
    """
    list the policies
    """
    P = PolicyClass()
    policies = P.get_policies()
    print "Active \t Name \t Scope"
    print 40*"="
    for policy in policies:
        print("%s \t %s \t %s" % (policy.get("active"), policy.get("name"),
                                  policy.get("scope")))


@policy_manager.command
def enable(name):
    """
    enable a policy by name
    """
    r = enable_policy(name)
    print r


@policy_manager.command
def disable(name):
    """
    disable a policy by name
    """
    r = enable_policy(name, False)
    print r


@policy_manager.command
def delete(name):
    """
    delete a policy by name
    """
    r = delete_policy(name)
    print r

@policy_manager.command
def create(name, scope, action):
    """
    create a new policy
    """
    r = set_policy(name, scope, action)
    return r

if __name__ == '__main__':
    manager.run()

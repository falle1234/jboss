#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: jboss_deploy

short_description: This module deploys applications to JBoss

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This is my longer description explaining my test module.

options:
  
  jboss_home:
    description:
      - Home directory for the JBoss EAP or Wildfly server.
    type: str
    aliases: ['wfly_home']
    required: True

  management_username:
    description:
      - Management username.
    type: str

  management_password:
    description:
      - Management password.
    type: str

  management_host:
    description:
      - Management host.
    type: str
    default: 'localhost'

  management_port:
    description:
      - Management port.
    type: str
    default: '9990'

  deployment:
    description:
      - Path to the deploymentfile.
    type: str
    required: True

# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
extends_documentation_fragment:
    - my_namespace.my_collection.my_doc_fragment_name

author:
    - Søren Bjørn-Fallesen (@falle1234akait)
'''

EXAMPLES = r'''
# Pass in a message
- name: Test with a message
  my_namespace.my_collection.my_test:
    name: hello world

# pass in a message and have changed true
- name: Test with a message and changed output
  my_namespace.my_collection.my_test:
    name: hello world
    new: true

# fail the module
- name: Test failure of the module
  my_namespace.my_collection.my_test:
    name: fail me
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
original_message:
    description: The original name param that was passed in.
    type: str
    returned: always
    sample: 'hello world'
message:
    description: The output message that the test module generates.
    type: str
    returned: always
    sample: 'goodbye'
'''
import subprocess
import json
import os
from ansible.module_utils.basic import AnsibleModule



def run_jboss_cli(data,command):
    """ execute the rules provided using jcliff """
    cli_command_line = ["bash", "-x",
                           data['jboss_home'] + "/bin/jboss-cli.sh",
                           "--controller=" +
                           data['management_host'] + ":" +
                           data['management_port'],
                           "-c"]

    if data["management_username"] is not None:
        cli_command_line.extend(["--user=" + data["management_username"]])
    if data["management_password"] is not None:
        cli_command_line.extend(
            ["--password=" + data["management_password"]])
    cli_command_line.extend(["--output-json"])
    cli_command_line.extend([command])
    try:
        output = subprocess.check_output(cli_command_line,
                                         stderr=subprocess.STDOUT,
                                         shell=False,
                                         env=os.environ)
        output = output.decode()
        output = output[output.index('\n{\n'):]
        result_parsed = json.loads(output)

    except Exception as exception:
        output = exception.output
        output = output.decode()
        idx = output.find('\n{\n')
        if idx >= 0:
            output = output[idx:]
            result_parsed = json.loads(output)
        else:
            result_parsed = dict()
        output = exception
        return (exception.returncode,result_parsed)
    return (0,result_parsed)


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        jboss_home=dict(required=True, aliases=['wfly_home'], type='str'),
        management_username=dict(required=False, type='str'),
        management_password=dict(required=False, type='str', no_log=True),
        management_host=dict(default='localhost', type='str'),
        management_port=dict(default='9990', type='str'),
        deployment_file=dict(required=True, type='str'),
        deployment=dict(required=True, type='str'),
        state=dict(choices=['present', 'absent', 'replace'], default='present'),
        tmp_dir=dict(required=False, type='str')
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        failed=False,
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # if the user is working with this module in only check mode we do not
    # want to make any changes to the environment, just return the current
    # state with no modifications
    if module.check_mode:
        module.exit_json(**result)



    state_map = {
        "present": deploy_present,
        "absent": deploy_absent,
        "replace": deploy_replace
    }

    has_changed, has_failed, log_data = state_map.get(
        module.params['state'])(params=module.params)
    module.exit_json(has_changed=has_changed,has_failed=has_failed,log_data=log_data)

    (return_code,json_data) = run_jboss_cli(module.params, '/deployment=' + module.params['deployment'] + ':read-resource(include-runtime=true)')
    result['log_data'] = json_data
    #raise Exception(json_data['result']['status'])
   
    
    if return_code > 0 and module.params['state'] == 'absent' and json_data['failure-description'].index('not found'):
        result['changed'] = False
        module.exit_json(**result)
    
    if return_code == 0 and module.params['state'] == 'absent' and json_data['outcome'] == 'success':
        result['changed'] = True
        module.exit_json(**result)

    # manipulate or modify the state as needed (this is going to be the
    # part where your module will do what it needs to do)
    result['original_message'] = module.params['deployment']

    # use whatever logic you need to determine whether or not this module
    # made any modifications to your target
    #if module.params['new']:
    #    result['changed'] = True

    # during the execution of the module, if there is an exception or a
    # conditional state that effectively causes a failure, run
    # AnsibleModule.fail_json() to pass in the message and the result
    #if module.params['name'] == 'fail me':
    #    module.fail_json(msg='You requested this to fail', **result)

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)

def deploy_present(params):
    (has_changed,has_failed,json_data) =(False,True,dict())
    (return_code,json_data) = get_deplyment_status(params)

    if return_code == 0 and json_data['result']['status'] == 'OK' and json_data['result']['enabled']:
        has_changed = False

    if return_code > 0 and json_data['failure-description'].index('not found'):
        (return_code, json_data) = run_jboss_cli(params,'deploy ' + params['tmp_dir'] + params['deployment'] +' --name '+ params['deployment'] + ' --force')
        if return_code == 0:
            has_changed = True
        else:
            has_failed = True

    return (has_changed, has_failed, json_data)

def deploy_absent(params):
    (return_code,json_data) = get_deplyment_status(params)
    return ('has_changed', 'has_failed', 'meta')

def deploy_replace(params):
    (return_code,json_data) = get_deplyment_status(params)
    return ('has_changed', 'has_failed', 'meta')

def main():
    run_module()

def get_deplyment_status(params):
    return run_jboss_cli(params, '/deployment=' + params['deployment'] + ':read-resource(include-runtime=true)')

if __name__ == '__main__':
    main()
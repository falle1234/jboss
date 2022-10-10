#!/usr/bin/python
# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.plugins.action import ActionBase



class ActionModule(ActionBase):

    TRANSFERS_FILES = True

    def run(self, tmp=None, task_vars=None):
        tmp_remote_src = self._make_tmp_path()
        result = super(ActionModule, self).run(tmp, task_vars)
        module_args = self._task.args.copy()
        module_args.update(dict(tmp_dir=tmp_remote_src,))
        self._transfer_file(self._task.args['deployment_file'], tmp_remote_src + self._task.args['deployment']+'.ear')
        result.update(self._execute_module(module_name='jboss_deploy',module_args=module_args,task_vars=task_vars))
        result['deployment_file'] = self._task.args['deployment_file']
        result['temp_file'] = tmp_remote_src + self._task.args['deployment']+'.ear'
        return result
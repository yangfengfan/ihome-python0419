#!/usr/bin/python
# -*- coding: utf-8 -*-

# tar -zcvf ihome-release2.1.2-2.tgz etc/ ihome smart_home/

import commands

print 'find ./main -name "*.pyc" | xargs rm -rf'
(status, output) = commands.getstatusoutput('find ./main -name "*.pyc" | xargs rm -rf')
print status, output

print 'rm -rf .git'  # 删除 .git 目录
(status, output) = commands.getstatusoutput('rm -rf .git')

print 'rm -rf .idea'  # 删除 .idea 目录
(status, output) = commands.getstatusoutput('rm -rf .idea')

print 'python -m compileall .'
(status, output) = commands.getstatusoutput('python -m compileall .')
print status, output

print 'find ./main -name "*.py" | xargs rm -rf'
(status, output) = commands.getstatusoutput('find ./main -name "*.py" | xargs rm -rf')
print status, output

print 'rm -rf ./main/static'
(status, output) = commands.getstatusoutput('rm -rf ./main/static')
print status, output


print 'rm -rf ./schema'
(status, output) = commands.getstatusoutput('rm -rf ./schema')
print status, output

print 'rm -rf ./.gitignore'
(status, output) = commands.getstatusoutput('rm -rf ./.gitignore')
print status, output

print 'rm -rf ./*.py*'
(status, output) = commands.getstatusoutput('rm -rf ./*.pyc')
print status, output

# test mod_md acme terms-of-service handling

import json
import os.path
import re
import shutil
import sys
import time
import pytest

from ConfigParser import SafeConfigParser
from datetime import datetime
from shutil import copyfile
from testbase import BaseTest

config = SafeConfigParser()
config.read('test.ini')

PREFIX = config.get('global', 'prefix')
A2MD = config.get('global', 'a2md_bin')
ACME_URL = config.get('acme', 'url')
WEBROOT = config.get('global', 'server_dir')
STORE_DIR = os.path.join(WEBROOT, 'md') 

def setup_module(module):
    print("setup_module: %s" % module.__name__)
        
def teardown_module(module):
    print("teardown_module: %s" % module.__name__)


class TestStore (BaseTest):

    def setup_method(self, method):
        print("setup_method: %s" % method.__name__)
        # wipe store directory
        print("clear store dir: %s" % STORE_DIR)
        assert len(STORE_DIR) > 1
        shutil.rmtree(STORE_DIR, ignore_errors=True)
        os.makedirs(STORE_DIR)
 
    def teardown_method(self, method):
        print("teardown_method: %s" % method.__name__)

    def test_001(self):
        # verify expected binary version
        args = [A2MD, "-V"]
        outdata = self.exec_sub(args)
        m = re.match("version: %s-git$" % config.get('global', 'a2md_version'), outdata)
        assert m

    # --------- store add ---------

    # add a single dns managed domain
    def test_100(self):
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns = "greenbytes.de"
        args.extend([ "store", "add", dns ])
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        md = jout['output'][0]
        assert md['name'] == dns
        assert len(md['domains']) == 1 
        assert md['domains'][0] == dns
        assert md['ca']['url'] == ACME_URL
        assert md['ca']['proto'] == 'ACME'
        assert md['state'] == 0

    # add > 1 dns managed domain
    def test_101(self):
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns = [ "greenbytes2.de", "www.greenbytes2.de", "mail.greenbytes2.de" ]
        args.extend([ "store", "add" ])
        args.extend(dns)
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        md = jout['output'][0]
        assert md['name'] == dns[0]
        assert len(md['domains']) == 3 
        assert md['domains'] == dns
        assert md['ca']['url'] == ACME_URL
        assert md['ca']['proto'] == 'ACME'
        assert md['state'] == 0

    # add second managed domain
    def test_102(self):
        # setup: add first managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns1 = [ "test-100.com", "test-101.com", "test-102.com" ]
        args.extend([ "store", "add" ])
        args.extend(dns1)
        self.exec_sub(args)
        # add second managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns2 = [ "greenbytes2.de", "www.greenbytes2.de", "mail.greenbytes2.de" ]
        args.extend([ "store", "add" ])
        args.extend(dns2)
        outdata = self.exec_sub(args)
        # assert: output covers only changed md
        jout = json.loads(outdata)
        assert len(jout['output']) == 1
        md = jout['output'][0]
        assert md['name'] == dns2[0]
        assert md['domains'] == dns2
        assert md['ca']['url'] == ACME_URL
        assert md['ca']['proto'] == 'ACME'
        assert md['state'] == 0

    # add existing domain 
    def test_103(self):
        # setup: add domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "add"])
        dns = "greenbytes.de"
        args.extend([dns])
        self.exec_sub(args)
        # add same domain again
        outdata = self.exec_sub_err(args, 1)

    # add without CA URL
    def test_104(self):
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "add"])
        dns = "greenbytes.de"
        args.extend([dns])
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        assert len(jout['output']) == 1
        md = jout['output'][0]
        assert md['name'] == dns
        assert md['domains'] == [ dns ]
        assert "url" not in md['ca']
        assert md['ca']['proto'] == 'ACME'
        assert md['state'] == 0

    # --------- store list ---------

    # list empty store
    def test_200(self):
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j", "store", "list" ]
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        assert 'output' not in jout
        assert jout['status'] == 0

    # list two managed domains
    def test_201(self):
        # setup: add managed domains
        dnslist = [ 
            [ "test-100.com", "test-101.com", "test-102.com" ], 
            [ "greenbytes2.de", "www.greenbytes2.de", "mail.greenbytes2.de"] 
        ]
        for dns in dnslist:
            args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j", "store", "add" ]
            args.extend(dns)
            self.exec_sub(args)
        # list all store content
        args = [A2MD, "-d", STORE_DIR, "-j", "store", "list" ]
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        assert len(jout['output']) == len(dnslist)
        dnslist.reverse()
        for i in range (0, len(jout['output'])):
            md = jout['output'][i]
            assert md['name'] == dnslist[i][0]
            assert md['domains'] == dnslist[i]
            assert md['ca']['url'] == ACME_URL
            assert md['ca']['proto'] == 'ACME'
            assert md['state'] == 0

    # --------- store remove ---------

    # remove managed domain
    def test_300(self):
        # setup: store managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns = "test-100.com"
        args.extend([ "store", "add", dns ])
        self.exec_sub(args)
        # remove managed domain
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "remove", dns ])
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        assert 'output' not in jout
        assert jout['status'] == 0
        # list store content
        args = [A2MD, "-d", STORE_DIR, "-j", "store", "list" ]
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        assert 'output' not in jout
        assert jout['status'] == 0

    # remove from list of managed domains 
    def test_301(self):
        # setup: add several managed domains
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns1 = [ "test-100.com", "test-101.com", "test-102.com" ]
        args.extend([ "store", "add"])
        args.extend(dns1)
        self.exec_sub(args)
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns2 = [ "greenbytes2.de", "www.greenbytes2.de", "mail.greenbytes2.de" ]
        args.extend([ "store", "add" ])
        args.extend(dns2)
        outdata = self.exec_sub(args)
        jout1 = json.loads(outdata)
        # remove managed domain
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "remove", "test-100.com" ])
        outdata = self.exec_sub(args)
        jout2 = json.loads(outdata)
        assert 'output' not in jout2
        assert jout2['status'] == 0
        # list store content
        args = [A2MD, "-d", STORE_DIR, "-j", "store", "list" ]
        outdata = self.exec_sub(args)
        jout2 = json.loads(outdata)
        assert len(jout2['output']) == 1
        assert jout1 == jout2

    # remove nonexisting managed domain
    def test_302(self):
	    # 1st try: error - not found
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        dns1 = "test-100.com"
        args.extend([ "store", "remove", dns1 ])
        outdata = self.exec_sub_err(args, 1)
        jout = json.loads(outdata)
        assert 'output' not in jout
        assert jout['status'] == 2

    # force remove nonexisting managed domain
    def test_303(self):
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        dns1 = "test-100.com"
        args.extend([ "store", "remove", "-f", dns1 ])
        outdata = self.exec_sub(args)
        jout = json.loads(outdata)
        assert 'output' not in jout
        assert jout['status'] == 0

    # --------- store update ---------

    # null change
    def test_400(self):
        # setup: store managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns = "test-100.com"
        args.extend([ "store", "add", dns ])
        outdata = self.exec_sub(args)
        jout1 = json.loads(outdata)
        # update without change
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "update", dns])
        outdata = self.exec_sub(args)
        jout2 = json.loads(outdata)
        assert len(jout2['output']) == 1
        assert jout1 == jout2

    # add dns to managed domain
    def test_401(self):
        # setup: store managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns1 = "test-100.com"
        args.extend([ "store", "add", dns1 ])
        outdata = self.exec_sub(args)
        jout1 = json.loads(outdata)
        # add second dns
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        dns2 = [ dns1, "test-101.com" ]
        args.extend([ "store", "update", dns1, "domains"])
        args.extend(dns2)
        outdata = self.exec_sub(args)
        jout2 = json.loads(outdata)
        assert len(jout2['output']) == 1
        jout1['output'][0]['domains'] = dns2
        assert jout2 == jout1

    # change CA URL
    def test_402(self):
        # setup: store managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns = "test-100.com"
        args.extend([ "store", "add", dns ])
        outdata = self.exec_sub(args)
        jout1 = json.loads(outdata)
        # change CA URL
        args = [A2MD, "-a", "https://foo.com/", "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "update", dns])
        outdata = self.exec_sub(args)
        jout2 = json.loads(outdata)
        assert len(jout2['output']) == 1
        jout1['output'][0]['ca']['url'] = "https://foo.com/"
        assert jout2 == jout1

    # update nonexisting managed domain
    def test_403(self):
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        dns = "test-100.com"
        args.extend([ "store", "update", dns ])
        self.exec_sub_err(args, 1)

    # update domains, throw away md name
    def test_406(self):
        # setup: store managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns1 = "test-100.com"
        args.extend([ "store", "add", dns1 ])
        outdata = self.exec_sub(args)
        jout1 = json.loads(outdata)
        # override domains list
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "update", dns1, "domains" ])
        dns2 = "greenbytes.com"
        args.extend([ dns2 ])
        outdata = self.exec_sub(args)
        jout2 = json.loads(outdata)
        assert len(jout2['output']) == 1
        jout1['output'][0]['domains'] = [ dns2 ]
        assert jout1 == jout2

    # update domains with empty dns list
    def test_407(self):
        # setup: store managed domain
        args = [A2MD, "-a", ACME_URL, "-d", STORE_DIR, "-j" ]
        dns1 = "test-100.com"
        args.extend([ "store", "add", dns1 ])
        self.exec_sub(args)
        # override domains list
        args = [A2MD, "-d", STORE_DIR, "-j" ]
        args.extend([ "store", "update", dns1, "domains" ])
        self.exec_sub_err(args, 1)